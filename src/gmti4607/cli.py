from __future__ import annotations
import argparse, json, sys
from .models.file import GmtiFile
from .viz import plot_detections

def cmd_info(args):
    from .models.file import GmtiFile

    # Fast path: summary or dry-run (with optional limits)
    if getattr(args, "summary", False) or getattr(args, "dry_run", False) or args.first_n_dwells or args.first_n_targets:
        from .binary.reader import summarize_file
        dwells, targets = summarize_file(
            args.input,
            max_dwells=args.first_n_dwells,
            max_targets=args.first_n_targets,
        )
        print(f"dwells={dwells}, targets={targets}")
        return
    
    # Sample with targets mode: only output dwells that contain targets
    if args.sample_with_targets:
        from .binary.reader import iter_dwells
        import json
        out = []
        dwells_with_targets = 0
        max_dwells_with_targets = args.sample_with_targets
        
        for dw in iter_dwells(
            args.input,
            decode_targets=True,
            max_targets_per_dwell=args.max_targets_per_dwell,
        ):
            # Only include dwells that have targets
            if dw.targets and len(dw.targets) > 0:
                dwells_with_targets += 1
                # Convert to plain dict to keep output small-ish
                out.append(dw.model_dump(mode="json"))
                
                # Stop when we've reached the limit
                if dwells_with_targets >= max_dwells_with_targets:
                    break
        
        print(json.dumps(out, indent=2))
        if dwells_with_targets == 0:
            print(f"Warning: No dwells with targets found in the file", file=sys.stderr)
        elif dwells_with_targets < max_dwells_with_targets:
            print(f"Warning: Only found {dwells_with_targets} dwells with targets (requested: {max_dwells_with_targets})", file=sys.stderr)
        return
    
    # Sample mode: decode a bounded subset with iterators
    if args.sample:
        from .binary.reader import iter_dwells
        import json
        out = []
        for dw in iter_dwells(
            args.input,
            decode_targets=True,
            max_dwells=args.sample,
            max_targets_per_dwell=args.max_targets_per_dwell,
        ):
            # Convert to plain dict to keep output small-ish
            out.append(dw.model_dump(mode="json"))
        print(json.dumps(out, indent=2))
        return
    
    # Full parse (heavier)
    f = GmtiFile.from_binary(args.input)
    import json
    print(json.dumps(f.model_dump(mode='json'), indent=2))

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
    sp.add_argument("--summary", action="store_true")
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

def main():
    p = argparse.ArgumentParser(prog="gmti4607")
    sub = p.add_subparsers()

    sp = sub.add_parser("info", help="print parsed model as JSON or a fast summary")
    sp.add_argument("input", help="Path to .4607 file")
    sp.add_argument("--summary", action="store_true", help="Print a fast summary (dwells, targets) without full parse")
    sp.add_argument("--dry-run", action="store_true", help="Scan structure only (no models); implies summary mode")
    sp.add_argument("--first-n-dwells", type=int, default=None, help="Stop after counting N dwells (summary/dry-run)")
    sp.add_argument("--first-n-targets", type=int, default=None, help="Stop after counting N targets (summary/dry-run)")
    sp.add_argument("--sample", type=int, default=None, help="Fully decode only the first N dwells (bounded)")
    sp.add_argument("--max-targets-per-dwell", type=int, default=500, help="Cap targets per dwell in sample mode")
    sp.add_argument("--sample-with-targets", type=int, help="Only output the first N dwells that contain targets")

    
    sp.set_defaults(func=cmd_info)

    ns = p.parse_args()
    if not hasattr(ns, "func"):
        p.print_help()
        return 2
    return ns.func(ns)


if __name__ == "__main__":
    raise SystemExit(main())
