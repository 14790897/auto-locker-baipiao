from dotenv import load_dotenv
import os
import requests

# 加载 .env 文件
load_dotenv()

issue_labels = os.getenv("ISSUE_LABELS", "haven't given me a star")
issue_labels = issue_labels.split(",")  # 将字符串转换为列表
issue_close_comment = os.getenv("ISSUE_CLOSE_COMMENT",
                                "Thank you for opening this issue. I noticed that you haven not given me a star yet, so I will close this issue. Please give me a star first and wait for it to be unlocked. Thank you for your understanding.")
issue_reopen_comment = os.getenv("ISSUE_REOPEN_COMMENT",
                                 "Thank you for giving me a star. I have unlocked this issue. If you have any questions, please feel free to ask. Thank you for your support.")
white_list = os.getenv("WIHTE_LIST", "")
white_list = white_list.split(",")  # 将字符串转换为列表
github_repo = os.getenv("GH_REPO")
github_token = os.getenv("GH_TOKEN")

headers = {
    'Authorization': 'Bearer ' + github_token,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
}


def get_stargazers(repo):
    page = 1
    _stargazers = {}
    while True:
        queries = {
            'per_page': 100,
            'page': page,
        }
        url = 'https://api.github.com/repos/{}/stargazers?'.format(repo)

        resp = requests.get(url, headers=headers, params=queries)
        if resp.status_code != 200:
            raise Exception('Error get stargazers: ' + resp.text)

        data = resp.json()
        if not data:
            break

        for stargazer in data:
            _stargazers[stargazer['login']] = True
        page += 1

    print('list stargazers done, total: ' + str(len(_stargazers)))
    return _stargazers


def get_issues(repo):
    page = 1
    _issues = []
    while True:
        queries = {
            "state": "all",
            "sort": "created",
            "direction": "desc",
            "per_page": 100,
            "page": page,
        }
        url = 'https://api.github.com/repos/{}/issues?'.format(repo)

        resp = requests.get(url, headers=headers, params=queries)
        if resp.status_code != 200:
            raise Exception('Error get issues: ' + resp.text)

        data = resp.json()
        if not data:
            break
        for issue in data:
            if issue["locked"] or issue["state"] == "open":
                _issues.append(issue)
        # _issues += data
        page += 1

    print('list issues done, total: ' + str(len(_issues)))
    return _issues


def close_issue(repo, issue_number):
    url = 'https://api.github.com/repos/{}/issues/{}'.format(repo, issue_number)
    data = {
        'state': 'closed',
        'state_reason': 'not_planned',
        'labels': issue_labels,
    }
    resp = requests.patch(url, headers=headers, json=data)
    if resp.status_code != 200:
        raise Exception('Error close issue: ' + resp.text)

    print('issue: {} closed'.format(issue_number))


def leave_comment(repo, issue_number, body):
    url = 'https://api.github.com/repos/{}/issues/{}/comments'.format(repo, issue_number)
    data = {
        'body': body,
    }
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code != 201:
        raise Exception('Error leave comment: ' + resp.text)

    print('issue: {} leave comment'.format(issue_number))


def lock_issue(repo, issue_number):
    url = 'https://api.github.com/repos/{}/issues/{}/lock'.format(repo, issue_number)
    data = {
        'lock_reason': 'spam',
    }
    resp = requests.put(url, headers=headers, json=data)
    if resp.status_code != 204:
        raise Exception('Error lock issue: ' + resp.text)

    print('issue: {} locked'.format(issue_number))


def unlock_issue(repo, issue_number):
    url = "https://api.github.com/repos/{}/issues/{}/lock".format(repo, issue_number)
    resp = requests.delete(url, headers=headers)
    if resp.status_code != 204:
        raise Exception("Error unlock issue: " + resp.text)

    print("issue: {} unlocked".format(issue_number))


def reopen_issue(repo, issue_number):
    url = "https://api.github.com/repos/{}/issues/{}".format(repo, issue_number)
    data = {
        "state": "open",
        "labels": [],
    }
    resp = requests.patch(url, headers=headers, json=data)
    if resp.status_code != 200:
        raise Exception("Error reopen issue: " + resp.text)

    print("issue: {} reopened".format(issue_number))


if '__main__' == __name__:
    stargazers = get_stargazers(github_repo)

    issues = get_issues(github_repo)
    for issue in issues:
        # 跳过pr
        if 'pull_request' in issue:
            continue
        # 跳过机器人
        if issue['user']['type'] == 'Bot':
            continue
        # 跳过白名单
        if issue['user']['login'] in white_list:
            continue

        login = issue['user']['login']
        if login not in stargazers:
            # 这里传入的既有锁定的也有打开的issue，我们只需要对未锁定的进行操作
            if not issue["locked"]:
                print(
                    "issue: {}, login: {} not in stargazers".format(
                        issue["number"], login
                    )
                )
                close_issue(github_repo, issue["number"])
                leave_comment(
                    github_repo,
                    issue["number"],
                    issue_close_comment,
                )
                lock_issue(github_repo, issue["number"])
        else:
            # 如果说用户是点过star的而且他的issue被锁定了且带有特定标签，就可以重新打开
            if issue["locked"]:
                # 检查是否带有特定标签
                has_label = False
                for label in issue["labels"]:
                    if label["name"] in issue_labels:
                        has_label = True
                        break
                if not has_label:
                    continue

                print(
                    "issue: {}, login: {} in stargazers".format(issue["number"], login)
                )
                unlock_issue(github_repo, issue["number"])
                leave_comment(
                    github_repo,
                    issue["number"],
                    issue_reopen_comment,
                )
                reopen_issue(github_repo, issue["number"])

    print('done')
