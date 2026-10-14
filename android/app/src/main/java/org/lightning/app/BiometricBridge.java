package org.lightning.app;

import android.app.Activity;
import android.hardware.biometrics.BiometricManager;
import android.hardware.biometrics.BiometricPrompt;
import android.os.Build;
import android.os.CancellationSignal;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyPermanentlyInvalidatedException;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.security.GeneralSecurityException;
import java.security.Key;
import java.security.KeyStore;
import java.security.UnrecoverableKeyException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import javax.crypto.AEADBadTagException;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Optional fingerprint unlock for the Python side (lightning.security.biometric, adapted in lightning_android.py).
 *
 * The profile's data key is wrapped by an Android Keystore AES-256-GCM key (alias lightning-bio-PROFILE) that
 * needs a strong biometric for every use. The wrap and the unwrap run only through a BiometricPrompt with a
 * CryptoObject: the Keystore releases the key to the cipher after the fingerprint, so a screen callback alone
 * never opens anything. The key is invalidated by Android when fingerprints are added or removed; then the answer
 * is "invalidated" and Python removes its slot. Nothing here keeps the data key: it passes through, as base64 in
 * and out, and Python holds it only while the profile is open.
 *
 * Framework APIs only (no AndroidX), API 30 and up: below that nothing is offered. Python calls arrive on a
 * worker thread; the prompt is shown on the UI thread and the worker waits on a latch, never the UI thread.
 * Answers are JSON {"status": ok | cancelled | lockout | invalidated | unavailable, "iv": base64, "data": base64}.
 */
@android.annotation.TargetApi(30)  // every entry is guarded by available(), which is false below API 30
public final class BiometricBridge {
    private static final String PROVIDER = "AndroidKeyStore";
    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int TAG_BITS = 128;
    private static final long WAIT_SECONDS = 60;
    static volatile Activity activity;

    private BiometricBridge() {}

    /** A strong biometric is enrolled and this Android can bind a key to it (API 30 and up). */
    public static boolean available() {
        Activity current = activity;
        if (Build.VERSION.SDK_INT < 30 || current == null) return false;
        try {
            BiometricManager manager = current.getSystemService(BiometricManager.class);
            return manager != null && manager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)
                    == BiometricManager.BIOMETRIC_SUCCESS;
        } catch (RuntimeException unavailable) {
            return false;
        }
    }

    /** Make a fresh Keystore key for the profile, ask for the fingerprint, and wrap `plaintextB64` under it. */
    public static String encrypt(String profileId, String plaintextB64, String aadB64) {
        if (!available()) return reply("unavailable", null, null);
        try {
            deleteKey(profileId);  // never reuse an older key: a new enrolment starts clean
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, newKey(profileId));
            Answer answer = ask(cipher, "Turn on fingerprint unlock");
            if (answer.cipher == null) {
                deleteKey(profileId);
                return reply(answer.status, null, null);
            }
            answer.cipher.updateAAD(Base64.decode(aadB64, Base64.NO_WRAP));
            byte[] wrapped = answer.cipher.doFinal(Base64.decode(plaintextB64, Base64.NO_WRAP));
            return reply("ok", answer.cipher.getIV(), wrapped);
        } catch (KeyPermanentlyInvalidatedException invalidated) {
            deleteKey(profileId);
            return reply("invalidated", null, null);
        } catch (GeneralSecurityException | RuntimeException failed) {
            deleteKey(profileId);
            return reply("unavailable", null, null);
        }
    }

    /** Ask for the fingerprint and unwrap `ciphertextB64` with the profile's Keystore key. */
    public static String decrypt(String profileId, String ivB64, String ciphertextB64, String aadB64) {
        if (!available()) return reply("unavailable", null, null);
        try {
            KeyStore store = KeyStore.getInstance(PROVIDER);
            store.load(null);
            Key key = store.getKey(alias(profileId), null);
            if (key == null) return reply("invalidated", null, null);  // the key is gone: the slot opens nothing
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, Base64.decode(ivB64, Base64.NO_WRAP)));
            Answer answer = ask(cipher, "Unlock with fingerprint");
            if (answer.cipher == null) return reply(answer.status, null, null);
            answer.cipher.updateAAD(Base64.decode(aadB64, Base64.NO_WRAP));
            return reply("ok", null, answer.cipher.doFinal(Base64.decode(ciphertextB64, Base64.NO_WRAP)));
        } catch (KeyPermanentlyInvalidatedException | UnrecoverableKeyException | AEADBadTagException invalidated) {
            return reply("invalidated", null, null);  // fingerprints changed, or the slot does not match the key
        } catch (GeneralSecurityException | java.io.IOException | RuntimeException failed) {
            return reply("unavailable", null, null);
        }
    }

    /** Remove the profile's Keystore key; harmless when there is none. */
    public static void deleteKey(String profileId) {
        try {
            KeyStore store = KeyStore.getInstance(PROVIDER);
            store.load(null);
            store.deleteEntry(alias(profileId));
        } catch (GeneralSecurityException | java.io.IOException | RuntimeException ignored) {
            // An orphan key opens nothing: its slot file is already gone.
        }
    }

    private static String alias(String profileId) {
        return "lightning-bio-" + profileId;
    }

    private static SecretKey newKey(String profileId) throws GeneralSecurityException {
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, PROVIDER);
        generator.init(new KeyGenParameterSpec.Builder(alias(profileId),
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .setUserAuthenticationRequired(true)
                .setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)  // every use, strong only (API 30)
                .setInvalidatedByBiometricEnrollment(true)
                .build());
        return generator.generateKey();
    }

    /** What the prompt came to: the authorised cipher, or why there is none. */
    private static final class Answer {
        final String status;
        final Cipher cipher;

        Answer(String status, Cipher cipher) {
            this.status = status;
            this.cipher = cipher;
        }
    }

    private static Answer ask(Cipher cipher, String title) {
        Activity current = activity;
        if (current == null) return new Answer("unavailable", null);
        CountDownLatch done = new CountDownLatch(1);
        AtomicReference<Answer> outcome = new AtomicReference<>(new Answer("unavailable", null));
        CancellationSignal cancel = new CancellationSignal();
        Executor main = current.getMainExecutor();
        current.runOnUiThread(() -> {
            try {
                BiometricPrompt prompt = new BiometricPrompt.Builder(current)
                        .setTitle(title)
                        .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
                        .setNegativeButton("Cancel", main, (dialog, which) -> {
                            outcome.set(new Answer("cancelled", null));
                            done.countDown();
                        })
                        .build();
                prompt.authenticate(new BiometricPrompt.CryptoObject(cipher), cancel, main,
                        new BiometricPrompt.AuthenticationCallback() {
                            @Override
                            public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result) {
                                BiometricPrompt.CryptoObject crypto = result.getCryptoObject();
                                outcome.set(crypto != null && crypto.getCipher() != null
                                        ? new Answer("ok", crypto.getCipher()) : new Answer("unavailable", null));
                                done.countDown();
                            }

                            @Override
                            public void onAuthenticationError(int code, CharSequence message) {
                                outcome.set(new Answer(statusOf(code), null));
                                done.countDown();
                            }
                            // onAuthenticationFailed: a finger that did not match. The sheet stays open and Android
                            // counts the tries (and locks out), so nothing to do here.
                        });
            } catch (RuntimeException failed) {
                outcome.set(new Answer("unavailable", null));
                done.countDown();
            }
        });
        try {
            if (!done.await(WAIT_SECONDS, TimeUnit.SECONDS)) {
                cancel.cancel();
                return new Answer("cancelled", null);
            }
        } catch (InterruptedException interrupted) {
            cancel.cancel();
            Thread.currentThread().interrupt();
            return new Answer("cancelled", null);
        }
        return outcome.get();
    }

    private static String statusOf(int code) {
        switch (code) {
            case BiometricPrompt.BIOMETRIC_ERROR_LOCKOUT:
            case BiometricPrompt.BIOMETRIC_ERROR_LOCKOUT_PERMANENT:
                return "lockout";
            case BiometricPrompt.BIOMETRIC_ERROR_CANCELED:
            case BiometricPrompt.BIOMETRIC_ERROR_USER_CANCELED:
            case BiometricPrompt.BIOMETRIC_ERROR_TIMEOUT:
                return "cancelled";
            default:
                return "unavailable";
        }
    }

    private static String reply(String status, byte[] iv, byte[] data) {
        try {
            JSONObject out = new JSONObject().put("status", status);
            if (iv != null) out.put("iv", Base64.encodeToString(iv, Base64.NO_WRAP));
            if (data != null) out.put("data", Base64.encodeToString(data, Base64.NO_WRAP));
            return out.toString();
        } catch (JSONException impossible) {
            return "{\"status\":\"unavailable\"}";
        }
    }
}
