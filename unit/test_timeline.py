from flux.tvm.timeline import TimelineManager

def test_create_timeline():
    tm = TimelineManager()
    tm.create("main")
    assert "main" in tm.list()
    tm.create("test", parent="main", weight=0.5)
    assert tm.get_weight("test") == 0.5

def test_merge():
    tm = TimelineManager()
    tm.create("A")
    tm.create("B")
    tm.merge("B", "A")
    assert "B" not in tm.list()