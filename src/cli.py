"""
Command-line interface for the quiz generator application.

This module provides argument parsing and CLI interaction for generating quizzes
from document files.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """
    Configure logging based on verbosity level.
    
    Args:
        verbose: Enable verbose output (INFO level)
        debug: Enable debug output (DEBUG level)
    """
    if debug:
        level = logging.DEBUG
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    elif verbose:
        level = logging.INFO
        format_str = '%(asctime)s - %(levelname)s - %(message)s'
    else:
        level = logging.WARNING
        format_str = '%(levelname)s: %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_input_files(input_paths: List[str]) -> List[Path]:
    """
    Validate that input files exist and are supported formats.
    
    Args:
        input_paths: List of file paths or glob patterns
        
    Returns:
        List of validated Path objects
        
    Raises:
        FileNotFoundError: If no valid files are found
        ValueError: If unsupported file format is provided
    """
    supported_extensions = {'.docx', '.pdf'}
    validated_files = []
    
    for input_path in input_paths:
        path = Path(input_path)
        
        # Handle glob patterns
        if '*' in input_path:
            parent = path.parent if path.parent.exists() else Path('.')
            pattern = path.name
            matched_files = list(parent.glob(pattern))
            
            for matched_file in matched_files:
                if matched_file.suffix.lower() in supported_extensions:
                    validated_files.append(matched_file)
        else:
            # Handle single file
            if not path.exists():
                raise FileNotFoundError(f"File not found: {input_path}")
            
            if path.suffix.lower() not in supported_extensions:
                raise ValueError(
                    f"Unsupported file format: {path.suffix}. "
                    f"Supported formats: {', '.join(supported_extensions)}"
                )
            
            validated_files.append(path)
    
    if not validated_files:
        raise FileNotFoundError("No valid input files found")
    
    return validated_files


def validate_output_directory(output_dir: Optional[str]) -> Path:
    """
    Validate and create output directory if needed.
    
    Args:
        output_dir: Output directory path (None for default)
        
    Returns:
        Path object for output directory
    """
    if output_dir is None:
        output_path = Path('./output')
    else:
        output_path = Path(output_dir)
    
    # Create directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    return output_path


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: List of arguments (None to use sys.argv)
        
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog='quiz_maker',
        description='Generate quizzes from student assignments using local LLMs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate quiz from a single document
  %(prog)s --input essay.docx
  
  # Process multiple files with custom output directory
  %(prog)s --input ./assignments/*.docx --output ./quizzes
  
  # Generate 10 questions in HTML format only
  %(prog)s --input essay.pdf --questions 10 --format html
  
  # Use different model with verbose output
  %(prog)s --input essay.docx --model mistral:7b --verbose
  
  # Debug mode for troubleshooting
  %(prog)s --input essay.docx --debug

For more information, visit: https://github.com/yourusername/quiz_maker
        """
    )
    
    # Required arguments
    parser.add_argument(
        '-i', '--input',
        required=True,
        nargs='+',
        metavar='FILE',
        help='Input document file(s) or glob pattern (e.g., *.docx)'
    )
    
    # Optional arguments
    parser.add_argument(
        '-o', '--output',
        metavar='DIR',
        help='Output directory for generated quizzes (default: ./output)'
    )
    
    parser.add_argument(
        '-q', '--questions',
        type=int,
        metavar='N',
        help='Number of questions to generate (default: from config.yaml)'
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['docx', 'html', 'both'],
        default='both',
        help='Output format (default: both)'
    )
    
    parser.add_argument(
        '-m', '--model',
        metavar='MODEL',
        help='Ollama model to use (default: from config.yaml)'
    )
    
    parser.add_argument(
        '-c', '--config',
        metavar='FILE',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--no-answer-key',
        action='store_true',
        help='Do not generate answer key'
    )
    
    parser.add_argument(
        '--no-explanations',
        action='store_true',
        help='Do not include explanations in answer key'
    )
    
    # Verbosity options
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output (INFO level)'
    )
    
    verbosity_group.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug output (DEBUG level)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser.parse_args(args)


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate parsed arguments and perform additional checks.
    
    Args:
        args: Parsed arguments namespace
        
    Raises:
        ValueError: If arguments are invalid
        FileNotFoundError: If required files don't exist
    """
    # Validate input files
    args.input_files = validate_input_files(args.input)
    
    # Validate output directory
    args.output_dir = validate_output_directory(args.output)
    
    # Validate config file
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {args.config}")
    args.config_path = config_path
    
    # Validate number of questions
    if args.questions is not None:
        if args.questions < 1:
            raise ValueError("Number of questions must be at least 1")
        if args.questions > 20:
            logging.warning(
                f"Generating {args.questions} questions may take a long time. "
                "Consider using a smaller number for faster results."
            )


def print_summary(args: argparse.Namespace) -> None:
    """
    Print a summary of the operation to be performed.
    
    Args:
        args: Parsed and validated arguments
    """
    print("\n" + "="*60)
    print("Quiz Generator - Configuration Summary")
    print("="*60)
    print(f"Input files: {len(args.input_files)}")
    for i, file in enumerate(args.input_files, 1):
        print(f"  {i}. {file.name}")
    print(f"Output directory: {args.output_dir}")
    print(f"Output format: {args.format}")
    if args.questions:
        print(f"Questions per quiz: {args.questions}")
    if args.model:
        print(f"LLM model: {args.model}")
    print(f"Generate answer key: {not args.no_answer_key}")
    if not args.no_answer_key:
        print(f"Include explanations: {not args.no_explanations}")
    print("="*60 + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point.
    
    Args:
        argv: Command-line arguments (None to use sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    args = None
    debug_mode = False
    
    try:
        # Parse arguments
        args = parse_arguments(argv)
        debug_mode = args.debug
        
        # Setup logging
        setup_logging(verbose=args.verbose, debug=args.debug)
        
        # Validate arguments
        validate_arguments(args)
        
        # Print summary if verbose
        if args.verbose or args.debug:
            print_summary(args)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if debug_mode:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
