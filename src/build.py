import json, sys, pathlib
here = pathlib.Path(__file__).parent
kb_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else here / "site" / "index.html"
kb = json.loads(kb_path.read_text("utf-8")) if kb_path and kb_path.exists() else {
    "problems": [{"id": "test", "title": "Pętelki od spodu", "symptoms": "test", "category": "scieg",
                  "causes": [{"cause": "Za luźna nić górna", "likelihood": "wysokie", "parts": ["tension_assembly"], "fix_steps": ["Dokręć"]}]}],
    "fabrics": [{"id": "jeans", "name": "Jeans", "needle": "Nm 110", "thread": "40", "stitch_mm": "3.0", "speed": "3000", "foot_pressure": "mocny", "upper_tension": "", "feed_mode": "ciężkie"}],
    "threading": {"upper": [{"step": 1, "text": "Stojak", "part": "thread_stand"}, {"step": 2, "text": "Naprężacz", "part": "tension_assembly"}, {"step": 3, "text": "Igła", "part": "needle"}]},
}
txt = json.dumps(kb, ensure_ascii=False).replace("</", "<\\/")
html = (here / "template.html").read_text("utf-8").replace("__KB__", txt)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, "utf-8")
print(out, len(html))
