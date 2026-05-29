from argparse import ArgumentParser

from src.core.directory_hash import DirectoryHasher


def build_parser():
    parser = ArgumentParser(description="usage")
    parser.add_argument(
        "path", type=str, help="The directory path to be check")

    parser.add_argument("--hash", type=str, default="sha256",
                        help="The hash algorithm used for checksum(default: sha256)")
    parser.add_argument("-v", "--verify", default=False, action="store_true",
                        help="Set ture to verify directory have or not changed(default: False)")
    return parser


def main(parser: ArgumentParser):
    args = parser.parse_args()
    DH = DirectoryHasher()
    DH.setDirectory(args.path)
    DH.setHashAlgorithm(args.hash)
    if args.verify:
        result = DH.verify()
        if result:
            print("Everything is OK!")
        else:
            result = DH.getErrorListReport()
            print("\n".join(result))
    else:
        DH._computeHash()
        DH.saveToFile()


if __name__ == "__main__":
    main(build_parser())
