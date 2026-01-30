import json
import re
import os
import time
import random
import subprocess
import textwrap
import configparser

def count_lines_in_jsonl(file_path):
    # 执行 wc -l 命令
    result = subprocess.run(['wc', '-l', file_path], capture_output=True, text=True)
    
    # result.stdout 的格式为 '  1234 your_file.jsonl'，需要提取数字
    line_count = int(result.stdout.split()[0])
    return line_count

def main():
    file_path = "./results_obfus/java/4bit_gru_srcmarker_42_csn_java_obfus_ALL_eval.jsonl"
    total_task = count_lines_in_jsonl(file_path)
    extract_success = 0
    obfus_extract_success_Msg = 0
    obfus_extract_success_Bit = 0
    raw_lines = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            raw_lines.append(line)
            
    for idx, line in enumerate(raw_lines):
        data = json.loads(line)
        for index, value in enumerate(data["watermark"]):
            if value == data["extract"][index] and value == data["obfus_extract"][index]:
                obfus_extract_success_Bit += 1
        if data["watermark"] == data["extract"]:
            extract_success += 1
            if data["extract"] == data["obfus_extract"]:
                obfus_extract_success_Msg += 1
    
    print("analysis: ")
    # print("obfus_type: Encrypt integer values using floating point math functions")
    print("obfus_type: Randomly renaming")
    print("language: java")
    print("watermark_bit: 4")
    print("total_task: " + str(total_task))
    # print("Watermark successfully embedded and extracted Tasks: " + str(extract_success))
    print("Bit Accuracy: " + str(obfus_extract_success_Bit/(total_task*4)))
    print("Msg Accuracy: " + str(obfus_extract_success_Msg/total_task))
    # print("Msg obfus extract success: " + str(obfus_extract_success))
    # print("Msg attack success rate: " + str(1-obfus_extract_success/extract_success))
    
if __name__ == "__main__":
    main()
