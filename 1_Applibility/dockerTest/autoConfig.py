from aiAPI import *
import json
import re
import time
import os
import argparse

def getDependency(client:Client, filePath:str, lang:str, max_retries=3, retry_delay=2) -> Optional[Dict]:
    """
    Get dependency configuration from the source file.
    :param file_path: File path
    :return: Dependency JSON
    """
    prompt = f"""
        Please analyze the {lang} code above and output dependency configuration in JSON format. Return only the JSON content, no extra text.
        ```json
        {{
            "jdk_version": "11", # Infer the appropriate JDK version based on Java features used. Output only the version number, e.g. `11`
            "dependencies": [ # List every external library dependency required by the Java code
                {{
                    "group": "com.example", # dependency groupId
                    "artifact": "example-artifact", # dependency artifactId
                    "version": "1.0.0" # dependency version
                }},
                ...
            ]
        }}
        ```
        Note:
        - If standard JDK libraries are used (such as `javax.swing`, `java.util`, etc.), do not include them.
        - Ensure every dependency has `group`, `artifact`, and `version` fields.
        - Include dependencies comprehensively so all required runtime libraries are covered.
    """
    retries = 0
    while retries < max_retries:
        try:
            deps = files_chat(client, Model.gpt4o_ca, [filePath], [prompt], StreamMode=True)
            # print(deps)
            match = re.search(r'```json(.*?)```', deps, re.DOTALL)
            if match:
                deps = match.group(1).strip()
                depsJson = json.loads(deps.replace("```json\n", "").replace("\n```", "").strip())
                return depsJson
            else:
                raise ValueError("No JSON content found in the response.")
        except Exception as e:
            retries += 1
            print(f"Error get {filePath} dependency: {e}")
            time.sleep(retry_delay)
    print("Max retries reached. Could not process the response successfully.")
    return None  # If max retries are reached and the response cannot be processed, return None


def genPOM(json_data, java_file_path):
    # Parse JSON data
    dependencies = json_data.get('dependencies', [])
    jdk_version = json_data.get('jdk_version', '11')  # Default to JDK 11

    # Get file directory
    project_dir = os.path.dirname(java_file_path)
    # Get file name (with extension)
    file_name = os.path.basename(java_file_path)
    # Get class name (without extension)
    class_name = os.path.splitext(file_name)[0]
    
    # Maven POM template
    pom_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
             http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>{class_name}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>jar</packaging>

    <properties>
        <maven.compiler.source>{jdk_version}</maven.compiler.source>
        <maven.compiler.target>{jdk_version}</maven.compiler.target>
    </properties>

    <dependencies>
'''

    # Add each dependency to pom.xml
    for dep in dependencies:
        group = dep.get('group', '')
        artifact = dep.get('artifact', '')
        version = dep.get('version', '')
        
        pom_content += f'''        <dependency>
            <groupId>{group}</groupId>
            <artifactId>{artifact}</artifactId>
            <version>{version}</version>
        </dependency>
'''

    # Close the dependencies section
    pom_content += '''    </dependencies>
</project>'''

    # Save pom.xml to the target directory
    pom_file_path = os.path.join(project_dir, 'pom.xml')
    with open(pom_file_path, 'w') as pom_file:
        pom_file.write(pom_content)

    print(f'pom.xml has been generated at: {pom_file_path}')

def autoConfig(client:Client, filePath:str, lang:str):
    """
    TODO: Automatically configure dependencies under the corresponding file directory
    :param client: AI API client
    :param filePath: File path
    :param lang: Language type
    """
    deps = getDependency(client, filePath, lang)
    if deps:
        genPOM(deps, filePath)
    else:
        raise RuntimeError("Failed to get dependencies from AI API.")

# if __name__ == '__main__':
#     # client = Client("./config/config.ini", "kimi")
#     client = Client("/home/zrz/.config/Personal_config/config_aiAPI.ini", "paid")
#     filePath = "/home/zrz/Projects/GitRepo/Repo/Python_Projects/VSCode/Python/CodeWM_AutoTest/results/stdDemo/CaroGame/CaroGame.java"
#     # deps = getDependency(client, filePath, "java")
#     # genPOM(deps, filePath)
#     autoConfig(client, filePath, "java")
#     # print(deps)

def main():
    # Parse command-line arguments using argparse
    parser = argparse.ArgumentParser(description='Process some inputs.')
    parser.add_argument('--filepath', type=str, help='Path to the file', required=True)
    parser.add_argument('--config', type=str, help='Path to the config file', default="/home/zrz/.config/Personal_config/config_aiAPI.ini")

    # Parse command-line arguments
    args = parser.parse_args()

    # Use the supplied filepath argument
    clientPath = args.config
    filePath = args.filepath 

    # Continue with the original logic
    client = Client(clientPath, "paid")
    autoConfig(client, filePath, "java")
    # print(deps)

if __name__ == '__main__':
    main()