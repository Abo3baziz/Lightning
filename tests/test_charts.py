

def test_each_trend_dot_knows_its_change_from_the_previous_point():
    from decimal import Decimal as D
    from lightning.ui.charts import trend
    chart = trend(["a", "b", "c"], [{"name": "Net worth", "tone": "good", "values": [D(100), D(110), D(99)]}])
    first, second, third = chart["series"][0]["dots"]
    assert first["change"] is None and first["pct"] is None
    assert second["change"] == 10 and round(second["pct"]) == 10
    assert third["change"] == -11 and round(third["pct"]) == -10
