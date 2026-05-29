import hashlib
import os

from src.utils.logger import getLogger


def calculateHash(file_path: str, hashAlgorithm: str):
    hasher = None
    logger = getLogger("hasher")
    if hashAlgorithm == "md5":
        hasher = hashlib.md5()
    elif hashAlgorithm == "sha256":
        hasher = hashlib.sha256()
    elif hashAlgorithm == "sha384":
        hasher = hashlib.sha384()
    elif hashAlgorithm == "sha512":
        hasher = hashlib.sha512()
    else:
        logger.error(f"hash algorithm {hashAlgorithm} not implemented.")
        raise NotImplementedError(
            f"hash algorithm {hashAlgorithm} not implemented.")
    logger.info(f"use hash algorithm {hashAlgorithm}")

    if file_path is None or not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    try:
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                hasher.update(block)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"calculateHash Error: {e}")
        return


def calculateDirHash(dir_path: str, hashAlgorithm: str) -> dict[str, str]:
    """
    不会被使用，主要用于测试目录遍历正确性
    """
    if not os.path.exists(dir_path):
        print("Path not exists")
        return

    if not os.path.isdir(dir_path):
        print("Path is a file")
        return

    result = {}
    for root, dirs, files in os.walk(dir_path):
        for file_name in files:
            if file_name == "checksum.json":
                continue
            file_path = os.path.join(root, file_name)
            hash_value = calculateHash(file_path, hashAlgorithm)
            # print("{}:\t{}".format(file_name, hash_value))
            result[file_path.replace(dir_path, ".")] = hash_value
    # print(json.dumps(result, indent=2))
    return result
