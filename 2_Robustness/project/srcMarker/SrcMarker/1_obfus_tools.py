#!/usr/bin/env python

###############################################################################
#
# JObfuscator WebApi interface usage example.
#
# In this example we will obfuscate sample source with default options.
#
# Version        : v1.04
# Language       : Python
# Author         : Bartosz Wójcik
# Web page       : https://www.pelock.com
#
###############################################################################

#
# include JObfuscator module
#
from jobfuscator import JObfuscator
from tqdm import tqdm
from argparse import ArgumentParser
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

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--code_mxlen", type=int, default=1400)
    parser.add_argument("--sample", action="store_true", help="Enable sample mode")
    parser.add_argument("--sample_size", type=int, default=50)
    parser.add_argument("--result_dir", type=str, default="./results_obfus")
    return parser.parse_args()

def obfus(myJObfuscator:JObfuscator, line:str):
    data = json.loads(line)  # 解析 JSON 行
    if "after_watermark" in data:  # 确保 "test" 字段存在
        sourceCode = data["after_watermark"]
        Wrapped_code = f"@Obfuscate\npublic class Example {{\n{sourceCode}\n}}"
        result = myJObfuscator.obfuscate_java_source(Wrapped_code)
        if result and "error" in result:
            # display obfuscated code
            if result["error"] == JObfuscator.ERROR_SUCCESS:
                # format output code for HTML display
                print(result["output"])
                # print(type(result["output"]))
                match = re.search(r"public class Example \{\n\n(.*)\n\}", result["output"], re.DOTALL)
                data["after_obfus"] = textwrap.dedent(match.group(1))
            else:
                data["after_obfus"] = ''
                print(f'An error occurred, error code: {result["error"]}')
        else:
            data["after_obfus"] = ''
            print("Something unexpected happen while trying to obfuscate the code.")
        json_data = json.dumps(data, ensure_ascii=False)
        return json_data
    else:
        return None
    
#
# if you don't want to use Python module, you can import directly from the file
#
#from pelock.jobfuscator import JObfuscator


def main(args):
    MXLEN = args.code_mxlen
    SAMPLE = args.sample
    SSIZE = args.sample_size
    RESULT_DIR = args.result_dir
    #
    # create JObfuscator class instance (we are using our activation key)
    #
    # 创建配置解析器
    config = configparser.ConfigParser()
    # 读取 .ini 文件
    config.read('config.ini')

    myJObfuscator = JObfuscator(config['default']['ID_Token'])
    myJObfuscator.enableCompression = True
    myJObfuscator.mixCodeFlow = True
    myJObfuscator.renameVariables = False
    myJObfuscator.renameMethods = True
    myJObfuscator.intsMathCrypt = True
    myJObfuscator.cryptStrings = True
    myJObfuscator.intsToArrays = True
    myJObfuscator.dblsToArrays = True


    #
    # source code in Java format
    #
    # 创建文件夹（如果已存在，则不会报错）
    json_src = "./results/4bit_gru_srcmarker_42_csn_java_test.jsonl"
    json_dest = "./results_obfus/4bit_gru_srcmarker_42_csn_java_tag1_1.jsonl"
    os.makedirs(RESULT_DIR, exist_ok=True)
    #读取log计数文件中已经执行到的位置
    if os.path.exists(json_dest):
        cur_idx = count_lines_in_jsonl(json_dest)
    else:
        cur_idx = 0
    print(cur_idx)

    raw_lines = []
    with open(json_src, "r", encoding="utf-8") as f:
        for line in f:
            raw_lines.append(line)

    
    if SAMPLE:
        #若进行采样，则选取采样数据后进行混淆
        json_lines = sorted(
            (line for line in raw_lines if len(json.loads(line).get("after_watermark", "")) <= MXLEN),
            key=lambda x: len(json.loads(x).get("after_watermark", "")),
            reverse=True
        )
        json_lines = json_lines[:SSIZE]
    else:
        json_lines = raw_lines
    
    for idx, line in tqdm(enumerate(json_lines),
                          total=len(json_lines),
                          desc="Processing lines", 
                          unit="line"):
        if idx < cur_idx:
            continue
        json_data = obfus(myJObfuscator, line)
        if json_data:
            with open(json_dest, "a", encoding="utf-8") as f:           
                f.write(json_data + '\n')
        time.sleep(random.randint(1, 3))



if __name__ == "__main__":
    args = parse_args()
    main(args)