from aiAPI import *
from tqdm import tqdm
from argparse import ArgumentParser
import json
import re
import os
import time
import random
import subprocess
import textwrap

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

def obfus(Client:Client, line:str):
    data = json.loads(line)  # 解析 JSON 行
    if "after_watermark" in data:  # 确保 "test" 字段存在
        sourceCode = data["after_watermark"]
        messages = [f"请你基于上传的java代码混淆规则文件中的第4条混淆规则即整数常量加密，将这段源码:{sourceCode}仿照此混淆规则进行混淆并给出结果，输出内容中除混淆后源码外不包含任何内容，以```java\n(混淆源码内容)\n```的格式输出"]
        if Client.CheckType() == 'Kimi':
            ans = common_chat(Client, Model.kimi_128k, messages, StreamMode=True, cache_tag="obfus_files")
        else:
            ans = files_chat(Client, Model.gpt4, ["./1_obfus_AI_rules.txt"], messages, StreamMode=True)
        pattern = re.compile(r'```java\n(.*?)\n```', re.DOTALL)
        match = pattern.search(ans)
        if match:
            data["after_obfus"] = textwrap.dedent(match.group(1))
            print(match.group(1))
        else:
            data["after_obfus"] = ''
            print("No match found")
        json_data = json.dumps(data, ensure_ascii=False)
        return json_data
    else:
        return None


def main(args):
    MXLEN = args.code_mxlen
    SAMPLE = args.sample
    SSIZE = args.sample_size
    RESULT_DIR = args.result_dir
    client = Client("/home/zrz/.config/Personal_config/config_aiAPI.ini", "paid")
    #
    # source code in Java format
    #
    # 创建文件夹（如果已存在，则不会报错）
    json_src = "./results/4bit_gru_srcmarker_42_csn_java_test.jsonl"
    json_dest = f"./results_obfus/4bit_gru_srcmarker_42_csn_java_test_obfus_ai_{client.CheckType()}_rules4.jsonl"
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
        json_data = obfus(client, line)
        if json_data:
            with open(json_dest, "a", encoding="utf-8") as f:           
                f.write(json_data + '\n')
        time.sleep(random.randint(1, 3))

if __name__ == '__main__':
    # client = Client("/home/zrz/.config/Personal_config/config_aiAPI.ini", "kimi")
    
    # cache_id = "cache-ezsruouoc6di11ggbfa1"
    # delete_cache_kimi(client, cache_id)

    # source_code = "protected final void fastPathOrderedEmit(U value, boolean delayError, Disposable disposable) {\n        final Observer<? super V> observer = downstream;\n        final SimplePlainQueue<U> q = queue;\n        if (wip.get() == 0 && wip.compareAndSet(0, 1)) {\n            if (q.isEmpty()) {\n                accept(observer, value);\n                if (leave(-1) == 0) {\n                    return;\n                }\n            } else {\n                q.offer(value);\n            }\n        } else {\n            q.offer(value);\n            if (!enter()) {\n                return;\n            }\n        }\n        QueueDrainHelper.drainLoop(q, observer, delayError, disposable, this);\n    }"
    # messages = [f"请你基于上传的java代码混淆规则文件中的第1条混淆规则，将这段源码:{source_code}仿照此混淆规则进行混淆并给出结果，输出内容中除混淆后源码外不包含任何内容"]

    # # files_chat(client, Model.kimi_128k, ["./1_obfus_AI_rules.txt"], [".."], StreamMode=True, cache_tag="obfus_files")
    
    # common_chat(client, Model.kimi_128k, messages, StreamMode=True, cache_tag="obfus_files")
    
    args = parse_args()
    main(args)
    