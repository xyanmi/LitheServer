#!/usr/bin/env python3
"""
LitheServer - Main entry point for command line usage
"""

import sys
import argparse
import os
from .server import LitheServer


def main():
    """Main entry point for the LitheServer application."""
    parser = argparse.ArgumentParser(
        description='LitheServer - A lightweight local file server with beautiful web interface',
        prog='litheserver'
    )
    
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=8000,
        help='Port to serve on (default: 8000)'
    )
    
    parser.add_argument(
        '-d', '--directory',
        type=str,
        default='.',
        help='Directory to serve (default: current directory)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'LitheServer {__import__("litheserver").__version__}'
    )
    
    args = parser.parse_args()
    
    # Validate directory
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.")
        sys.exit(1)
    
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory.")
        sys.exit(1)
    
    # Create and start server
    server = LitheServer(
        host=args.host,
        port=args.port,
        directory=args.directory
    )
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down LitheServer...")
        server.stop()
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 