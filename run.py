"""Explicit preview launcher. The production client is not implemented yet."""
import argparse

def main():
    
    parser = argparse.ArgumentParser(description="Chatters desktop application")
    
    
    parser.add_argument("--demo", action="store_true", help="Run the local desktop preview; no networking")
    args = parser.parse_args()
    if not args.demo:
        parser.error("The network client is not available yet. Use --demo for the local preview.")
    from client.ui.app import main as run_preview
    return run_preview()

if __name__ == '__main__':
    raise SystemExit(main())
