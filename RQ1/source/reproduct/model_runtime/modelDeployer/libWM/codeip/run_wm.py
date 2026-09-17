from .wm import main, WmBaseArgs
from transformers import HfArgumentParser


def cli() -> None:
    parser = HfArgumentParser((WmBaseArgs,))
    args, = parser.parse_args_into_dataclasses()
    main(args)


if __name__ == "__main__":
    cli()
