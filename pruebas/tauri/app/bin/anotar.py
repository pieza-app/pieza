import json, os, sys
d = json.load(open(sys.argv[-2]))
open(os.path.join(os.environ["PRUEBA_DATOS"], "visto.json"), "w").write(d["texto"])
json.dump({"ok": True}, open(sys.argv[-1], "w"))
