#!/usr/bin/env python3
"""
Quiz Maker - Main Entry Point

Generate quizzes from student assignments using local LLMs.
This script orchestrates all components to process documents and create quizzes.
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

from src.cli import parse_arguments, validate_arguments, setup_logging, print_summary
from src.config_manager import ConfigManager
from src.document_processor import DocumentProcessor
from src.quiz_generator import QuizGenerator
from src.output_formatter import OutputFormatter
from src.models import Quiz


logger = logging.getLogger(__name__)


def process_single_document(
    input_file: Path,
    output_dir: Path,
    quiz_generator: QuizGenerator,
    output_formatter: OutputFormatter,
    args
) -> bool:
    """
    Process a single document and generate quiz.
    
    Args:
        input_file: Path to input document
        output_dir: Directory for output files (used only if config dirs not set)
        quiz_generator: QuizGenerator instance
        output_formatter: OutputFormatter instance
        args: CLI arguments namespace
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Processing: {input_file.name}")
        print(f"\n📄 Processing: {input_file.name}")
        
        # Generate quiz
        print("  ⚙️  Generating quiz...")
        quiz = quiz_generator.generate_quiz_from_document(
            doc_path=str(input_file),
            num_questions=args.questions
        )
        
        if not quiz or not quiz.questions:
            logger.error(f"Failed to generate quiz for {input_file.name}")
            print(f"  ❌ Failed to generate quiz")
            return False
        
        print(f"  ✅ Generated {len(quiz.questions)} questions")
        
        # Create base filename from input file
        base_name = input_file.stem
        
        # Determine formats to generate
        formats_to_generate = []
        if args.format in ['docx', 'both']:
            formats_to_generate.append('docx')
        if args.format in ['html', 'both']:
            formats_to_generate.append('html')
        
        # Generate quiz outputs using the proper method that respects config
        print("  ⚙️  Creating quiz files...")
        quiz_outputs = output_formatter.create_quiz_outputs(
            quiz=quiz,
            base_filename=base_name,
            output_dir=str(output_dir) if args.output else None,  # Use CLI output only if explicitly provided
            formats=formats_to_generate
        )
        
        for fmt, path in quiz_outputs.items():
            icon = "📝" if fmt == 'docx' else "🌐"
            print(f"  {icon} Created: {path}")
        
        # Generate answer key if requested
        if not args.no_answer_key:
            print("  ⚙️  Creating answer key files...")
            answer_outputs = output_formatter.create_answer_key_outputs(
                quiz=quiz,
                base_filename=base_name,
                output_dir=str(output_dir) if args.output else None,  # Use CLI output only if explicitly provided
                formats=formats_to_generate
            )
            
            for fmt, path in answer_outputs.items():
                icon = "📝" if fmt == 'docx' else "🌐"
                print(f"  {icon} Created: {path}")
        
        print(f"  ✅ Successfully processed {input_file.name}")
        logger.info(f"Successfully processed {input_file.name}")
        
        return True
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"  ❌ Error: File not found - {e}")
        return False
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(f"  ❌ Error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error processing {input_file.name}: {e}", exc_info=True)
        print(f"  ❌ Error: {e}")
        return False


def process_documents(
    input_files: List[Path],
    output_dir: Path,
    config_manager: ConfigManager,
    args
) -> tuple[int, int]:
    """
    Process multiple documents and generate quizzes.
    
    Args:
        input_files: List of input document paths
        output_dir: Directory for output files
        config_manager: Configuration manager instance
        args: CLI arguments namespace
        
    Returns:
        Tuple of (successful_count, failed_count)
    """
    # Initialize components
    logger.info("Initializing quiz generator components")
    
    try:
        quiz_generator = QuizGenerator(config_manager)
        output_formatter = OutputFormatter(config_manager.config)
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}", exc_info=True)
        print(f"\n❌ Failed to initialize quiz generator: {e}", file=sys.stderr)
        return 0, len(input_files)
    
    # Process each document
    successful = 0
    failed = 0
    
    for i, input_file in enumerate(input_files, 1):
        print(f"\n[{i}/{len(input_files)}]", end=" ")
        
        if process_single_document(
            input_file,
            output_dir,
            quiz_generator,
            output_formatter,
            args
        ):
            successful += 1
        else:
            failed += 1
    
    return successful, failed


def print_final_summary(successful: int, failed: int, output_dir: Path, config_manager: ConfigManager) -> None:
    """
    Print final summary of processing results.
    
    Args:
        successful: Number of successfully processed documents
        failed: Number of failed documents
        output_dir: Output directory path (from CLI)
        config_manager: Configuration manager to get actual output directories
    """
    print("\n" + "="*60)
    print("Processing Complete")
    print("="*60)
    print(f"✅ Successful: {successful}")
    if failed > 0:
        print(f"❌ Failed: {failed}")
    
    # Show actual output directories
    quiz_dir = config_manager.get('output.quiz_dir', './output/quizzes')
    answer_key_dir = config_manager.get('output.answer_key_dir', './output/answer_keys')
    
    print(f"📁 Quiz directory: {Path(quiz_dir).absolute()}")
    print(f"📁 Answer key directory: {Path(answer_key_dir).absolute()}")
    print("="*60 + "\n")


def check_ollama_availability() -> bool:
    """
    Check if Ollama is available and running.
    
    Returns:
        True if Ollama is available, False otherwise
    """
    try:
        import ollama
        # Try to list models to verify connection
        ollama.list()
        return True
    except ImportError:
        logger.error("Ollama package not installed")
        print("\n❌ Error: Ollama package not installed", file=sys.stderr)
        print("Install with: pip install ollama", file=sys.stderr)
        return False
    except Exception as e:
        logger.error(f"Ollama not available: {e}")
        print("\n❌ Error: Cannot connect to Ollama", file=sys.stderr)
        print("Make sure Ollama is installed and running:", file=sys.stderr)
        print("  1. Install: https://ollama.ai/download", file=sys.stderr)
        print("  2. Start: ollama serve", file=sys.stderr)
        print("  3. Pull model: ollama pull llama3.1:8b", file=sys.stderr)
        return False


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for quiz maker application.
    
    Args:
        argv: Command-line arguments (None to use sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    args = None
    debug_mode = False
    
    try:
        # Parse and validate arguments
        args = parse_arguments(argv)
        debug_mode = args.debug
        
        # Setup logging
        setup_logging(verbose=args.verbose, debug=args.debug)
        
        # Validate arguments
        validate_arguments(args)
        
        # Print summary if verbose
        if args.verbose or args.debug:
            print_summary(args)
        
        # Check Ollama availability
        if not check_ollama_availability():
            return 1
        
        # Load configuration
        logger.info(f"Loading configuration from {args.config_path}")
        config_manager = ConfigManager(str(args.config_path))
        
        # Override config with CLI arguments if provided
        if args.model:
            config_manager.set('llm.model', args.model)
            logger.info(f"Using model from CLI: {args.model}")
        
        if args.questions:
            config_manager.set('quiz.default_questions', args.questions)
            logger.info(f"Using question count from CLI: {args.questions}")
        
        if args.no_explanations:
            config_manager.set('output.include_explanations', False)
        
        # Process documents
        logger.info(f"Processing {len(args.input_files)} document(s)")
        print(f"\n🚀 Starting quiz generation for {len(args.input_files)} document(s)...")
        
        successful, failed = process_documents(
            args.input_files,
            args.output_dir,
            config_manager,
            args
        )
        
        # Print final summary
        print_final_summary(successful, failed, args.output_dir, config_manager)
        
        # Return appropriate exit code
        if failed > 0 and successful == 0:
            return 1  # All failed
        elif failed > 0:
            return 2  # Some failed
        else:
            return 0  # All successful
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        if debug_mode:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
