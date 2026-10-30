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
    args,
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
            doc_path=str(input_file), num_questions=args.questions
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
        if args.format in ["docx", "both"]:
            formats_to_generate.append("docx")
        if args.format in ["html", "both"]:
            formats_to_generate.append("html")

        # Generate quiz outputs using the proper method that respects config
        print("  ⚙️  Creating quiz files...")
        quiz_outputs = output_formatter.create_quiz_outputs(
            quiz=quiz,
            base_filename=base_name,
            output_dir=str(output_dir)
            if args.output
            else None,  # Use CLI output only if explicitly provided
            formats=formats_to_generate,
        )

        for fmt, path in quiz_outputs.items():
            icon = "📝" if fmt == "docx" else "🌐"
            print(f"  {icon} Created: {path}")

        # Generate answer key if requested
        if not args.no_answer_key:
            print("  ⚙️  Creating answer key files...")
            answer_outputs = output_formatter.create_answer_key_outputs(
                quiz=quiz,
                base_filename=base_name,
                output_dir=str(output_dir)
                if args.output
                else None,  # Use CLI output only if explicitly provided
                formats=formats_to_generate,
            )

            for fmt, path in answer_outputs.items():
                icon = "📝" if fmt == "docx" else "🌐"
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
    input_files: List[Path], output_dir: Path, config_manager: ConfigManager, args
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
    # Initialize components once so the GGUF model is reused across documents
    logger.info("Initializing quiz generator components")

    try:
        quiz_generator = QuizGenerator(config_manager)
        output_formatter = OutputFormatter(config_manager.config)
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}", exc_info=True)
        model_path = config_manager.get("llm.model_path", "./models/model.gguf")
        print(
            f"\n❌ Failed to initialize local LLM ({model_path}): {e}", file=sys.stderr
        )
        print(
            "Verify that the GGUF file exists, is readable, and fits in memory with the "
            "configured llm.n_ctx and llm.n_gpu_layers settings.",
            file=sys.stderr,
        )
        return 0, len(input_files)

    # Process each document
    successful = 0
    failed = 0

    for i, input_file in enumerate(input_files, 1):
        print(f"\n[{i}/{len(input_files)}]", end=" ")

        if process_single_document(
            input_file, output_dir, quiz_generator, output_formatter, args
        ):
            successful += 1
        else:
            failed += 1

    return successful, failed


def print_final_summary(
    successful: int, failed: int, output_dir: Path, config_manager: ConfigManager
) -> None:
    """
    Print final summary of processing results.

    Args:
        successful: Number of successfully processed documents
        failed: Number of failed documents
        output_dir: Output directory path (from CLI)
        config_manager: Configuration manager to get actual output directories
    """
    print("\n" + "=" * 60)
    print("Processing Complete")
    print("=" * 60)
    print(f"✅ Successful: {successful}")
    if failed > 0:
        print(f"❌ Failed: {failed}")

    # Show actual output directories
    quiz_dir = config_manager.get("output.quiz_dir", "./output/quizzes")
    answer_key_dir = config_manager.get("output.answer_key_dir", "./output/answer_keys")

    print(f"📁 Quiz directory: {Path(quiz_dir).absolute()}")
    print(f"📁 Answer key directory: {Path(answer_key_dir).absolute()}")
    print("=" * 60 + "\n")


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

        # Build CLI configuration overrides before validating config
        overrides = {}
        if args.model:
            overrides["llm"] = {"model_path": args.model}
            logger.info(f"Using GGUF model path from CLI: {args.model}")

        if args.questions:
            overrides["quiz"] = {"default_questions": args.questions}
            logger.info(f"Using question count from CLI: {args.questions}")

        if args.no_explanations:
            overrides["output"] = {"include_explanations": False}

        # Load and validate configuration
        logger.info(f"Loading configuration from {args.config_path}")
        config_manager = ConfigManager(str(args.config_path), overrides=overrides)

        # Process documents
        logger.info(f"Processing {len(args.input_files)} document(s)")
        print(
            f"\n🚀 Starting quiz generation for {len(args.input_files)} document(s)..."
        )

        successful, failed = process_documents(
            args.input_files, args.output_dir, config_manager, args
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


if __name__ == "__main__":
    sys.exit(main())
