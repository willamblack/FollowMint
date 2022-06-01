import json
import threading
import time
import requests
from blocknative.stream import Stream
from web3 import Web3
from eth_abi import decode_abi
import os

configExample = {
    "RPC": "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161",
    "privateKey": ["", ""],
    "blocknativeKey": "",
    "barkKey": "",
    "maxGasPrice": 50,
    "maxGasLimit": 1000000,
    "follow": {
        "0x8888887a5e2491fec904d90044e6cd6c69f1e71c": {"start": 0, "end": 24},
        "0x555555B63d1C3A8c09FB109d2c80464685Ee042B": {"start": 18, "end": 6},
        "0x99999983c70de9543cdc11dB5DE66A457d241e8B": {"start": 8, "end": 20}
    },
    "blacklist": ["Ape", "Bear", "Duck", "Pixel", "Not", "Okay", "Woman", "Baby", "Goblin", "Ai"]
}


def print_green(message):
    stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
    print(f'[{stime}] \033[1;32m{message}\033[0m')


def print_red(message):
    stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
    print(f'[{stime}] \033[1;31m{message}\033[0m')


def print_blue(message):
    stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
    print(f'[{stime}]\033[1;34m{message}\033[0m')


def print_yellow(message):
    stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
    print(f'[{stime}]\033[1;33m{message}\033[0m')


def bark(info, data):
    if barkKey != '':
        requests.get('https://api.day.app/' + barkKey + '/' + info + '?url=' + data)


def getMethodName(methodSignature):
    try:
        if methodSignature in methodNameDict:
            print_yellow(methodNameDict[methodSignature]['method'])
            return methodNameDict[methodSignature]['isMint'], methodNameDict[methodSignature]['method']
        res = requests.get('https://www.4byte.directory/api/v1/signatures/?hex_signature=' + methodSignature)
        if res.status_code == 200:
            method = res.json()['results'][0]['text_signature']
            methodName = method.split('(')[0].lower()
            print_yellow(method)
            if 'mint' in methodName:
                methodNameDict[methodSignature] = {'method': method, 'isMint': True}
                return True, method
            else:
                methodNameDict[methodSignature] = {'method': method, 'isMint': False}
        return False, None
    except:
        return False, None


def isBlackList(_to):
    try:
        NFTcon = w3.eth.contract(address=_to, abi=[nameabi])
        name = NFTcon.functions.name().call()
        for black in blacklist:
            if black in name:
                print_yellow(name + "黑名单，跳过")
                return False
    except:
        print_yellow('获取NFT名称失败，跳过')
        return False
    return True


def isMintTime(_from):
    for _follow in follows:
        if _follow.lower() == _from.lower():
            starttime = int(follows[_follow]['start'])
            endtime = int(follows[_follow]['end'])
            tm_hour = time.localtime().tm_hour
            if tm_hour >= starttime or tm_hour < endtime:
                pass
            else:
                print_yellow("非Mint时间，跳过")
                return False
    return True


def minttx(_account, _privateKey, _inputData, _method, _from_address, _to_address, _gasPrice, _maxFeePerGas, _maxPriorityFeePerGas):
    try:
        abi = _method.split('(')[1][:-1].split(',')
        if len(abi) != 0 and 'address' in abi:
            params = decode_abi(['uint256', 'address'], bytes.fromhex(_inputData[10:]))
            for index in range(len(abi)):
                if abi[index] == 'address':
                    _inputData = _inputData.replace(params[index][2:].lower(), _account.address[2:].lower())
        transaction = {
            'from': _account.address,
            'chainId': chainId,
            'to': _to_address,
            'gas': 2000000,
            'nonce': w3.eth.getTransactionCount(_account.address),
            'data': _inputData
        }
        if _gasPrice > 10000:
            transaction['gasPrice'] = _gasPrice
        else:
            transaction['maxFeePerGas'] = _maxFeePerGas
            transaction['maxPriorityFeePerGas'] = _maxPriorityFeePerGas
        try:
            estimateGas = w3.eth.estimateGas(transaction)
            if estimateGas > maxGasLimit:
                print_yellow('超过gasLimit上限，跳过')
                return
            transaction['gas'] = estimateGas
            signed = w3.eth.account.sign_transaction(transaction, _privateKey)
            new_raw = signed.rawTransaction.hex()
            tx_hash = w3.eth.sendRawTransaction(new_raw)
            print_green("mint交易发送成功" + w3.toHex(tx_hash))
            freceipt = w3.eth.waitForTransactionReceipt(tx_hash, 600)
            if freceipt.status == 1:
                print_green("mint成功")
                bark('mint成功', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
            else:
                print_green("mint失败")
                bark('mint失败', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
        except Exception as e:
            print_yellow('预测失败，跳过:' + str(e))
            return
    except Exception as e:
        print_yellow('发送交易失败，跳过:' + str(e))
        return


async def txn_handler(txn, unsubscribe):
    to_address = txn['to']
    from_address = txn['from']
    to_address = w3.toChecksumAddress(to_address)
    gasPrice = 0
    maxFeePerGas = 0
    maxPriorityFeePerGas = 0
    if 'gasPrice' in txn:
        gasPrice = int(txn['gasPrice']) + 1000000
    else:
        maxFeePerGas = int(txn['maxFeePerGas'])
        maxPriorityFeePerGas = int(txn['maxPriorityFeePerGas']) + 1000000
    inputData = txn['input']
    value = txn['value']
    print_yellow(from_address + "监控到新交易")
    if not isMintTime(from_address):
        return
    if value != '0':
        print_yellow("非免费，跳过")
        return
    if to_address in mintadd:
        print_yellow("mint过，跳过")
        return
    isMint, method = getMethodName(inputData[:10])
    if not isMint:
        print_yellow('可能不是mint交易,跳过')
        return
    if not isBlackList(to_address):
        return
    if gasPrice > maxGasPrice or maxFeePerGas > maxGasPrice:
        print_yellow('gasPrice过高,跳过')
        return
    mintadd.append(to_address)
    for index in range(len(accounts)):
        threading.Thread(target=minttx, args=(accounts[index], privateKeys[index], inputData, method, from_address, to_address, gasPrice, maxFeePerGas, maxPriorityFeePerGas)).start()


def main():
    while True:
        try:
            stream = Stream(blocknativeKey)
            print_blue(str(len(accounts)) + '个地址开始监控')
            print_blue('开始监控')
            for _follow in follows:
                filters = [{
                    "status": "pending",
                    "from": _follow
                }]
                stream.subscribe_address(_follow, txn_handler, filters)
            stream.connect()
        except Exception as e:
            print_red(str(e))
            time.sleep(10)


if __name__ == '__main__':
    print_red("有能力的请使用源码，本打包版本不对使用者安全负责")
    print_red("打狗请用小号，无法保证无bug")
    print_red("开源地址：https://github.com/Fooyao/FollowMint")
    print_red("代码水平较差，有任何优化建议请反馈")
    if not os.path.exists('config.json'):
        print_blue('请先配置config.json')
        file = open('config.json', 'w')
        file.write(json.dumps(configExample))
        file.close()
        time.sleep(10)
    try:
        file = open('config.json', 'r')
        config = json.loads(file.read())
        RPC = config['RPC']
        privateKeys = config['privateKey']
        if type(privateKeys) == str:
            privateKeys = [privateKeys]
            file = open('config.json', 'w')
            config['privateKey'] = privateKeys
            file.write(json.dumps(config))
            file.close()
        if 'blacklist' in config:
            blacklist = config['blacklist']
        else:
            blacklist = []
            file = open('config.json', 'w')
            config['blacklist'] = ["Ape", "Bear", "Duck", "Pixel", "Not", "Okay", "Woman", "Baby", "Goblin", "Ai"]
            file.write(json.dumps(config))
            file.close()
        blocknativeKey = config['blocknativeKey']
        barkKey = config['barkKey']
        follows = config['follow']
        nameabi = {
            'inputs': [],
            'name': 'name',
            'outputs': [{'internalType': 'string', 'name': '', 'type': 'string'}],
            'stateMutability': 'view',
            'type': 'function'
        }
        if type(follows) == list:
            print_red('请重新配置follow起始时间，配置文件模板已更新')
            followsDict = {}
            for follow in follows:
                followsDict[follow] = {'start': 0, 'end': 24}
            config['follow'] = followsDict
            file = open('config.json', 'w')
            file.write(json.dumps(config))
            file.close()
            time.sleep(10)
        else:
            w3 = Web3(Web3.HTTPProvider(RPC))
            maxGasPrice = config['maxGasPrice']
            maxGasPrice = w3.toWei(maxGasPrice, 'gwei')
            maxGasLimit = int(config['maxGasLimit'])
            chainId = w3.eth.chainId
            accounts = []
            for privateKey in privateKeys:
                accounts.append(w3.eth.account.privateKeyToAccount(privateKey))
            mintadd = []
            methodNameDict = {}
            main()
    except Exception as e:
        print_red(str(e))
        time.sleep(10)
