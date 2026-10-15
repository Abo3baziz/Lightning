"""Optional fingerprint unlock on the phone (task 18d): a device-bound slot outside the profile folder, opened
only through the phone's bridge (a fake here, with a real AES-GCM Keystore stand-in), then the same unlock road as
the password. What cannot be tested without a phone (the Java bridge, the system prompt) is in NOW.md."""
import base64
import json
import os

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.testclient import TestClient

from lightning.runtime.app import profile_app
from lightning.runtime.devices import Devices
from lightning.runtime.http import Credentials
from lightning.runtime.session import AttemptGuard, ProfileError, ProfileSession
from lightning.security.biometric import BridgeResult, FingerprintUnlock, Outcome, SlotStore

from test_profile_app import PASSWORD, SECRET, create, token

NEW_PASSWORD = "another correct long passphrase"


class FakeBridge:
    """The phone: a Keystore that keeps one AES key per profile and a fingerprint reader that says what the
    test scripted (the next answers, in order; `ok` when nothing is left)."""

    def __init__(self):
        self.is_available = True
        self.script = []
        self.keys = {}
        self.deleted = []
        self.prompts = 0
        self.wrong_key = False

    def available(self):
        return self.is_available

    def _answer(self):
        self.prompts += 1
        return self.script.pop(0) if self.script else Outcome.OK

    def encrypt(self, profile_id, plaintext, aad):
        outcome = self._answer()
        if outcome is not Outcome.OK:
            return BridgeResult(outcome)
        key = self.keys.setdefault(profile_id, AESGCM.generate_key(256))
        iv = os.urandom(12)
        return BridgeResult(Outcome.OK, iv, AESGCM(key).encrypt(iv, plaintext, aad))

    def decrypt(self, profile_id, iv, ciphertext, aad):
        outcome = self._answer()
        if outcome is not Outcome.OK:
            return BridgeResult(outcome)
        if profile_id not in self.keys:
            return BridgeResult(Outcome.INVALIDATED)
        try:
            data = AESGCM(self.keys[profile_id]).decrypt(iv, ciphertext, aad)
        except InvalidTag:
            return BridgeResult(Outcome.UNAVAILABLE)
        return BridgeResult(Outcome.OK, b"", os.urandom(32) if self.wrong_key else data)

    def delete_key(self, profile_id):
        self.deleted.append(profile_id)
        self.keys.pop(profile_id, None)


def phone_app(tmp_path, bridge, *, phone=True, port=9871):
    cfg = Credentials(f"http://127.0.0.1:{port}")
    unlock = FingerprintUnlock(tmp_path / "app" / "biometric", bridge) if bridge is not None else None
    app = profile_app(cfg, tmp_path / "docs", devices=Devices(tmp_path / "app", port=0), phone=phone, biometric=unlock)
    browser = TestClient(app, base_url=cfg.origin, headers={"Origin": cfg.origin})
    return browser, app, cfg, unlock


def opened(browser, cfg):
    browser.get("/__launch", params={"code": cfg.launch_code})
    create(browser)


def turn_on(browser, password=PASSWORD):
    csrf = token(browser.get("/profiles/fingerprint").text)
    return browser.post("/profiles/fingerprint", data={"csrf": csrf, "action": "on", "password": password})


def lock(browser):
    csrf = token(browser.get("/profiles").text)
    browser.post("/profiles/lock", data={"csrf": csrf})


def use_fingerprint(browser, db):
    page = browser.get("/profiles/unlock", params={"db": db})
    return browser.post("/profiles/unlock/fingerprint", data={"csrf": token(page.text), "db": db})


@pytest.fixture
def phone(tmp_path):
    bridge = FakeBridge()
    browser, app, cfg, unlock = phone_app(tmp_path, bridge)
    with browser:
        opened(browser, cfg)
        yield browser, app, bridge, unlock, tmp_path


def db_of(app):
    return str(app.session.paths.db_path)


# ------------------------------------------------------------------ the slot
def test_enrol_then_unlock_opens_the_profile(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    key = app.session.sync_key
    page = turn_on(browser)
    assert page.status_code == 200 and "Fingerprint unlock is on" in page.text
    assert unlock.enabled(profile_id)
    lock(browser)
    assert app.session.container is None
    assert "Use fingerprint" in browser.get("/profiles/unlock", params={"db": db}).text
    response = use_fingerprint(browser, db)
    assert response.status_code == 200 and app.session.container is not None
    assert app.session.sync_key == key


def test_the_slot_never_holds_the_raw_key_and_sits_outside_the_profile(phone):
    browser, app, bridge, unlock, tmp_path = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    key = app.session.sync_key
    profile_folder = app.session.paths.data_dir
    turn_on(browser)
    path = unlock.store.path(profile_id)
    assert path.parent == tmp_path / "app" / "biometric" and profile_folder not in path.parents
    raw = path.read_bytes()
    for form in (key, key.hex().encode(), base64.b64encode(key), base64.urlsafe_b64encode(key)):
        assert form not in raw
    document = json.loads(raw)
    assert set(document) == {"version", "profile_id", "key_id", "iv", "ciphertext", "created"}
    assert document["key_id"] == __import__("lightning.security.keys", fromlist=["key_id"]).key_id(key)
    assert key not in (profile_folder / "keys.json").read_bytes()
    assert (path.stat().st_mode & 0o077) == 0 or os.name == "nt"


def test_turning_on_needs_the_password_typed_again(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    page = turn_on(browser, "not the password at all")
    assert page.status_code == 400 and "The password is incorrect." in page.text
    assert not unlock.enabled(profile_id) and bridge.prompts == 0
    assert AttemptGuard(app.session.paths.keys_path.with_name("attempts.json")).wait_left() == 0


def test_turning_on_cancelled_leaves_nothing(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    bridge.script = [Outcome.CANCELLED]
    page = turn_on(browser)
    assert page.status_code == 400 and "was not turned on" in page.text
    assert not unlock.enabled(profile_id)
    assert not unlock.store.path(profile_id).exists() and bridge.keys == {}


def test_cancel_leaves_the_password_screen_and_counts_no_attempt(phone):
    browser, app, bridge, unlock, tmp_path = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    turn_on(browser)
    lock(browser)
    bridge.script = [Outcome.CANCELLED]
    page = use_fingerprint(browser, db)
    assert app.session.container is None and "Enter your password" in page.text and "alert-error" not in page.text
    assert "Use fingerprint" in page.text  # the slot stays
    assert not list((tmp_path / "docs").rglob("attempts.json"))


def test_lockout_keeps_the_slot_and_says_so(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    turn_on(browser)
    lock(browser)
    bridge.script = [Outcome.LOCKOUT]
    page = use_fingerprint(browser, db)
    assert app.session.container is None and "Too many fingerprint tries" in page.text
    assert unlock.enabled(profile_id)


def test_invalidated_removes_slot_and_key_and_tells_the_person(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    turn_on(browser)
    lock(browser)
    bridge.script = [Outcome.INVALIDATED]
    page = use_fingerprint(browser, db)
    assert app.session.container is None and "fingerprints changed" in page.text
    assert "Unlock with your password, then turn fingerprint on again." in page.text
    assert not unlock.store.path(profile_id).exists() and profile_id in bridge.deleted
    assert "Use fingerprint" not in page.text


def test_a_key_that_is_not_this_profiles_is_refused_and_removed(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    turn_on(browser)
    lock(browser)
    bridge.wrong_key = True
    page = use_fingerprint(browser, db)
    assert app.session.container is None and "no longer matches this profile" in page.text
    assert not unlock.store.path(profile_id).exists() and profile_id in bridge.deleted


def test_a_slot_for_another_key_id_is_refused_before_the_prompt(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    turn_on(browser)
    document = json.loads(unlock.store.path(profile_id).read_text())
    document["key_id"] = "0" * 16
    unlock.store.path(profile_id).write_text(json.dumps(document))
    lock(browser)
    prompts = bridge.prompts
    page = use_fingerprint(browser, db)
    assert app.session.container is None and bridge.prompts == prompts and "no longer matches" in page.text
    assert not unlock.store.path(profile_id).exists() and profile_id in bridge.deleted


def test_a_damaged_slot_is_dropped_and_the_button_hidden(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    turn_on(browser)
    unlock.store.path(profile_id).write_text("{not json")
    lock(browser)
    assert "Use fingerprint" not in browser.get("/profiles/unlock", params={"db": db}).text
    assert not unlock.store.path(profile_id).exists()


def test_turning_off_deletes_the_slot_and_the_keystore_key(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    turn_on(browser)
    assert profile_id in bridge.keys
    csrf = token(browser.get("/profiles/fingerprint").text)
    page = browser.post("/profiles/fingerprint", data={"csrf": csrf, "action": "off"})
    assert "Fingerprint unlock is off" in page.text
    assert not unlock.store.path(profile_id).exists() and profile_id in bridge.deleted and profile_id not in bridge.keys
    lock(browser)
    assert "Use fingerprint" not in browser.get("/profiles/unlock", params={"db": db}).text


def test_changing_the_password_keeps_fingerprint_unlock_working(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    key = app.session.sync_key
    turn_on(browser)
    keys_path = app.session.paths.keys_path  # the key file is rewritten by the change; the data key is not
    before = json.loads(unlock.store.path(profile_id).read_text())
    changed = browser.post("/profiles/password", data={"csrf": token(browser.get("/profiles").text), "proof": SECRET["answer"],
                                                         "password": NEW_PASSWORD, "confirm": NEW_PASSWORD})
    assert "Password changed" in changed.text
    assert json.loads(unlock.store.path(profile_id).read_text()) == before and keys_path.exists()
    lock(browser)
    assert use_fingerprint(browser, db).status_code == 200
    assert app.session.sync_key == key
    lock(browser)  # and the new password still opens it
    csrf = token(browser.get("/profiles/unlock", params={"db": db}).text)
    browser.post("/profiles/unlock", data={"csrf": csrf, "db": db, "password": NEW_PASSWORD})
    assert app.session.container is not None


# ------------------------------------------------------------------ the session road
def test_unlock_with_key_takes_the_same_checks_as_a_password(tmp_path, monkeypatch):
    from lightning.runtime.restore import EncryptedBackupRestorer
    session = ProfileSession(tmp_path / "profiles")
    session.prepare("Home", PASSWORD, PASSWORD, "What was the name of your first school?", "El Orman")
    session.confirm(session.pending.recovery)
    key, db = session.container.db.copy_key(), str(session.paths.db_path)
    session.close()

    def blocked(paths, data_key):
        raise ProfileError("A restore is waiting to be checked.")
    monkeypatch.setattr(EncryptedBackupRestorer, "_check_restore_control", staticmethod(blocked))
    with pytest.raises(ProfileError, match="restore is waiting"):
        session.unlock_with_key(db, key)
    assert session.container is None
    monkeypatch.undo()
    session.unlock_with_key(db, key)
    assert session.container is not None and session.role.writable
    session.close()
    with pytest.raises(ProfileError, match="does not belong"):
        session.unlock_with_key(db, os.urandom(32))
    session.unlock(db, PASSWORD)  # the failed try released the instance lock and counted nothing
    assert session.container is not None
    assert not AttemptGuard(session.paths.keys_path.with_name("attempts.json")).path.exists()


# ------------------------------------------------------------------ when it is offered
def test_the_option_is_hidden_when_the_phone_cannot_offer_it(tmp_path):
    bridge = FakeBridge()
    bridge.is_available = False
    browser, app, cfg, unlock = phone_app(tmp_path, bridge, port=9872)
    with browser:
        opened(browser, cfg)
        assert "Unlock with fingerprint" not in browser.get("/settings").text
        assert browser.get("/profiles/fingerprint", follow_redirects=False).status_code == 303
        csrf = token(browser.get("/profiles").text)
        assert browser.post("/profiles/fingerprint", data={"csrf": csrf, "action": "on", "password": PASSWORD},
                            follow_redirects=False).status_code == 303
        assert bridge.prompts == 0 and not unlock.store.folder.exists()
        bridge.is_available = True
        db = str(app.session.paths.db_path)
        assert "Unlock with fingerprint" in browser.get("/settings").text
        turn_on(browser)
        lock(browser)
        bridge.is_available = False  # fingerprints removed from the phone: the button goes, the password stays
        assert "Use fingerprint" not in browser.get("/profiles/unlock", params={"db": db}).text


def test_the_option_is_hidden_on_the_pc_and_without_a_bridge(tmp_path):
    bridge = FakeBridge()
    for number, (phone_mode, given) in enumerate(((False, bridge), (True, None))):
        folder = tmp_path / str(number)
        browser, app, cfg, unlock = phone_app(folder, given, phone=phone_mode, port=9873 + number)
        if given is not None:
            unlock.bridge = bridge
        with browser:
            opened(browser, cfg)
            assert "Unlock with fingerprint" not in browser.get("/settings").text
            assert browser.get("/profiles/fingerprint", follow_redirects=False).status_code == 303
            lock(browser)
            db = str(app.session.paths.db_path) if app.session.paths else ""
            assert "Use fingerprint" not in browser.get("/profiles/unlock", params={"db": db}).text
            assert bridge.prompts == 0


def test_the_settings_row_and_the_pages_speak_arabic_too(phone):
    browser, app, bridge, unlock, _ = phone
    db, profile_id = db_of(app), app.session.paths.profile.profile_id
    browser.post("/settings/locale", data={"locale": "ar", "__session": token(browser.get("/settings").text, "__session")})
    row = browser.get("/settings").text
    assert "افتح ببصمة الإصبع" in row and ">Unlock with fingerprint<" not in row
    page = browser.get("/profiles/fingerprint").text
    assert "شغّل البصمة" in page and ">Turn on fingerprint<" not in page
    turn_on(browser)
    lock(browser)
    unlock_page = browser.get("/profiles/unlock", params={"db": db}).text
    assert "استخدم البصمة" in unlock_page and ">Use fingerprint<" not in unlock_page


def test_slot_store_refuses_odd_profile_ids(tmp_path):
    store = SlotStore(tmp_path)
    for bad in ("../x", "a/b", "", "ZZZZZZZZ", "abc"):
        with pytest.raises(ValueError):
            store.path(bad)


def test_the_android_adapter_speaks_the_java_bridges_json():
    """`lightning_android.AndroidBiometric` over a stand-in for the Java class: base64 strings in, JSON out."""
    import importlib
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "android" / "app" / "src" / "main" / "python"))
    try:
        sys.modules.pop("lightning_android", None)
        phone_module = importlib.import_module("lightning_android")
    finally:
        sys.path.pop(0)

    class Java:
        seen = []

        @staticmethod
        def available():
            return True

        @staticmethod
        def encrypt(profile_id, plaintext_b64, aad_b64):
            Java.seen.append((profile_id, base64.b64decode(plaintext_b64), base64.b64decode(aad_b64)))
            return json.dumps({"status": "ok", "iv": base64.b64encode(b"i" * 12).decode(),
                               "data": base64.b64encode(b"c" * 48).decode()})

        @staticmethod
        def decrypt(profile_id, iv_b64, ciphertext_b64, aad_b64):
            return json.dumps({"status": "invalidated"})

        @staticmethod
        def deleteKey(profile_id):
            Java.seen.append(("deleted", profile_id))

    adapter = phone_module.AndroidBiometric(Java)
    assert adapter.available() is True
    made = adapter.encrypt("abcd1234", b"k" * 32, b"aad")
    assert made == BridgeResult(Outcome.OK, b"i" * 12, b"c" * 48) and Java.seen[0] == ("abcd1234", b"k" * 32, b"aad")
    assert adapter.decrypt("abcd1234", b"i" * 12, b"c" * 48, b"aad") == BridgeResult(Outcome.INVALIDATED)
    adapter.delete_key("abcd1234")
    assert Java.seen[-1] == ("deleted", "abcd1234")
    assert phone_module.AndroidBiometric.create() is None  # off the phone there is no Java: nothing is offered
