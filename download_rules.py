import requests
import os
import re
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504, 404, 403],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def convert_to_mirror_urls(url):
    """将GitHub原始链接转换为多个镜像链接"""
    mirrors = []
    
    # 原始链接
    mirrors.append(url)
    
    # 对于gist链接的处理
    if 'gist.githubusercontent.com' in url:
        # ghproxy镜像 - 完整URL
        mirrors.append(f"https://ghproxy.com/{url}")
        # ghproxy镜像 - 不带https
        mirrors.append(f"https://ghproxy.com/{url.replace('https://', '')}")
        
    # 对于普通GitHub raw链接的处理
    elif 'raw.githubusercontent.com' in url:
        parts = url.split('raw.githubusercontent.com/')[1].split('/')
        user = parts[0]
        repo = parts[1]
        branch = parts[2]
        path = '/'.join(parts[3:])
        
        # JSDelivr镜像
        mirrors.append(f"https://cdn.jsdelivr.net/gh/{user}/{repo}@{branch}/{path}")
        # ghproxy镜像 - 完整URL
        mirrors.append(f"https://ghproxy.com/{url}")
        # ghproxy镜像 - 不带https
        mirrors.append(f"https://ghproxy.com/{url.replace('https://', '')}")
        # fastgit镜像 
        mirrors.append(f"https://raw.fastgit.org/{user}/{repo}/{branch}/{path}")
        # statically镜像
        mirrors.append(f"https://cdn.statically.io/gh/{user}/{repo}/{branch}/{path}")

    return mirrors

def download_file(url, folder, filename):
    os.makedirs(folder, exist_ok=True)
    
    session = create_session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 获取所有镜像链接
    mirror_urls = convert_to_mirror_urls(url)
    print(f"\nDownloading {filename}...")
    
    # 依次尝试每个镜像
    for i, mirror_url in enumerate(mirror_urls, 1):
        try:
            print(f"Trying mirror {i}/{len(mirror_urls)}: {mirror_url}")
            response = session.get(mirror_url, headers=headers, timeout=5)
            response.raise_for_status()
            
            filepath = os.path.join(folder, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Successfully downloaded: {filename}")
            break
            
        except requests.Timeout:
            print(f"Mirror {i} timed out after 5 seconds, skipping...")
            if i == len(mirror_urls):
                print(f"All mirrors timed out for {filename}")
        except Exception as e:
            print(f"Mirror {i} failed: {str(e)}")
            if i == len(mirror_urls):
                print(f"All mirrors failed for {filename}")
    
    time.sleep(1)

def extract_rules_from_ini(ini_path):
    rules = {}
    try:
        with open(ini_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        pattern = r'ruleset=.*?,(\bhttps?://[^\s,]+)'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            url = match.group(1)
            filename = url.split('/')[-1]
            rules[filename] = url
        
        print(f"Found {len(rules)} rules to download")
        return rules
        
    except Exception as e:
        print(f"Error reading INI file: {str(e)}")
        return {}

# 从配置文件提取规则
ini_path = 'config/test.ini'
rules = extract_rules_from_ini(ini_path)

# 下载所有规则文件
for filename, url in rules.items():
    download_file(url, "rules", filename) 