from __future__ import annotations
import argparse, json, sys
from .models.file import GmtiFile
from .viz import plot_detections

def cmd_info(args):
    f = GmtiFile.from_binary(args.input)
    print(json.dumps(f.model_dump(mode="json"), indent=2))

def cmd_to_xml(args):
    f = GmtiFile.from_binary(args.input)
    xml = f.to_xml(validate=args.validate, pretty=True)
    with open(args.output, "w", encoding="utf-8") as out:
        out.write(xml)

def cmd_from_xml(args):
    f = GmtiFile.from_xml(args.input)
    data = f.to_binary()
    with open(args.output, "wb") as out:
        out.write(data)

def cmd_to_json(args):
    f = GmtiFile.from_binary(args.input)
    with open(args.output, "w", encoding="utf-8") as out:
        json.dump(f.model_dump(mode="json"), out, indent=2)

def cmd_plot(args):
    f = GmtiFile.from_binary(args.input)
    if args.mode == "detections":
        plot_detections(f)
    else:
        print("Unknown plot mode", file=sys.stderr)
        sys.exit(2)

def build_parser():
    p = argparse.ArgumentParser(prog="gmti4607", description="STANAG 4607 GMTI utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("info", help="print parsed model as JSON")
    sp.add_argument("input")
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("to-xml", help="convert binary to XML")
    sp.add_argument("input")
    sp.add_argument("output")
    sp.add_argument("--validate", action="store_true")
    sp.set_defaults(func=cmd_to_xml)

    sp = sub.add_parser("from-xml", help="convert XML to binary")
    sp.add_argument("input")
    sp.add_argument("output")
    sp.set_defaults(func=cmd_from_xml)

    sp = sub.add_parser("to-json", help="convert binary to JSON")
    sp.add_argument("input")
    sp.add_argument("output")
    sp.set_defaults(func=cmd_to_json)

    sp = sub.add_parser("plot", help="minimal verification plot(s)")
    sp.add_argument("input")
    sp.add_argument("--mode", default="detections", choices=["detections"])
    sp.set_defaults(func=cmd_plot)

    return p

def main(argv=None):
    parser = build_parser()
    ns = parser.parse_args(argv)
    ns.func(ns)

if __name__ == "__main__":
    main()
