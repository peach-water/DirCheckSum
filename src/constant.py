

HASH_ALGORITHM = ["sha256", "md5", "sha384", "sha512"]


FILE_LOST = 1  # 对比哈希计算结果发现文件缺失
FILE_CHANGED = 2  # 发现文件有变化
FILE_NEW_ADD = 3  # 发现有新文件加入

FILE_STATUS = {
    FILE_LOST: "缺失",
    FILE_CHANGED: "变化",
    FILE_NEW_ADD: "新增",
}