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
    "privateKey": ["私钥1", "私钥2"],
    "blocknativeKey": "监控平台key",
    "barkKey": "IOS推送软件key",
    "scanApikey": "https://etherscan.io/register注册获取",
    "maxGasPrice": 50,
    "maxGasLimit": 1000000,
    "maxValue": 0,
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


def getETHPrice():
    params = {
        'module': 'stats',
        'action': 'ethprice',
        'apikey': scanApikey
    }
    res = requests.get('https://api.etherscan.io/api', params=params)
    if res.status_code == 200 and res.json()['status'] == '1':
        return float(res.json()['result']['ethusd'])


def getMethodName(methodSignature, _conadd):
    try:
        if methodSignature in methodNameDict:
            print_blue('mint方法：' + methodNameDict[methodSignature]['method'])
            return methodNameDict[methodSignature]['isMint'], methodNameDict[methodSignature]['method']
        res = requests.get('https://www.4byte.directory/api/v1/signatures/?hex_signature=' + methodSignature)
        if res.status_code == 200 and res.json()['count'] > 0:
            method = res.json()['results'][0]['text_signature']
            methodName = method.split('(')[0].lower()
            print_blue('mint方法：' + method)
            if 'mint' in methodName:
                methodNameDict[methodSignature] = {'method': method, 'isMint': True}
                return True, method
            else:
                methodNameDict[methodSignature] = {'method': method, 'isMint': False}
        else:
            params = {
                'module': 'contract',
                'action': 'getabi',
                'address': _conadd,
                'apikey': scanApikey
            }
            res = requests.get('https://api.etherscan.io/api', params=params)
            if res.status_code == 200 and res.json()['status'] == '1':
                abi = res.json()['result']
                NFTcon = w3.eth.contract(address=w3.toChecksumAddress(_conadd), abi=abi)
                abiinfo = NFTcon.get_function_by_selector(methodSignature)
                method = str(abiinfo)[10:-1]
                print_blue('mint方法：' + method)
                if 'mint' in method.split('(')[0].lower():
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
                print_red(name + "黑名单" + black + "，跳过")
                return False
    except:
        print_red('获取NFT名称失败，跳过')
        return False
    print_blue('NFT名称：' + name)
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
                print_red("非Mint时间，跳过")
                return False
    return True


def getgas():
    headers = {"Authorization": blocknativeKey}
    url = 'https://api.blocknative.com/gasprices/blockprices?confidenceLevels=95'
    res = requests.get(url=url, headers=headers)
    if res.status_code == 200:
        estimatedPrices = res.json()['blockPrices'][0]['estimatedPrices'][0]
        maxPriorityFeePerGas = estimatedPrices['maxPriorityFeePerGas']
        maxFeePerGas = estimatedPrices['maxFeePerGas']
        baseFee = estimatedPrices['price']
        maxPriorityFeePerGas = w3.toWei(maxPriorityFeePerGas + 0.1, 'gwei')
        maxFeePerGas = w3.toWei(maxFeePerGas + 0.1, 'gwei')
        baseFee = w3.toWei(baseFee + 0.1, 'gwei')
        return baseFee, maxFeePerGas, maxPriorityFeePerGas


def minttx(_account, _privateKey, _inputData, _method, _from_address, _to_address, _maxFeePerGas, _maxPriorityFeePerGas, _value):
    try:
        abi = _method.split('(')[1][:-1].split(',')
        if len(abi) != 0 and 'address' in abi:
            params = decode_abi(abi, bytes.fromhex(_inputData[10:]))
            for index in range(len(abi)):
                if abi[index] == 'address':
                    _inputData = _inputData.replace(params[index][2:].lower(), _account.address[2:].lower())
        transaction = {
            'from': _account.address,
            'chainId': chainId,
            'to': _to_address,
            'gas': 2000000,
            'maxFeePerGas': _maxFeePerGas,
            'maxPriorityFeePerGas': _maxPriorityFeePerGas,
            'nonce': w3.eth.getTransactionCount(_account.address),
            'data': _inputData,
            'value': _value
        }
        try:
            estimateGas = w3.eth.estimateGas(transaction)
            if estimateGas > maxGasLimit:
                print_red('超过gasLimit上限，跳过')
                return
            transaction['gas'] = int(estimateGas * 1.2)
            signed = w3.eth.account.sign_transaction(transaction, _privateKey)
            new_raw = signed.rawTransaction.hex()
            tx_hash = w3.eth.sendRawTransaction(new_raw)
            print_green("mint交易发送成功" + w3.toHex(tx_hash))
            freceipt = w3.eth.waitForTransactionReceipt(tx_hash, 600)
            if freceipt.status == 1:
                try:
                    ETHused = freceipt.effectiveGasPrice * freceipt.gasUsed
                    ETHused = float(w3.fromWei(ETHused, 'ether'))
                    USDuse = ETHPrice * ETHused
                    ETHusedinfo = '本次mint：' + str(USDuse) + ' U'
                except Exception as e:
                    print(str(e))
                    ETHusedinfo = ''
                print_green("mint成功   " + ETHusedinfo)
                bark('mint成功', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
            else:
                print_red("mint失败")
                mintadd.remove(_to_address)
                bark('mint失败', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
        except Exception as e:
            print_red('预测失败，跳过:' + str(e))
            mintadd.remove(_to_address)
            return
    except Exception as e:
        print_red('发送交易失败，跳过:' + str(e))
        return


async def txn_handler(txn, unsubscribe):
    to_address = txn['to']
    from_address = txn['from']
    to_address = w3.toChecksumAddress(to_address)
    inputData = txn['input']
    value = int(txn['value'])
    print_yellow(from_address + "监控到新交易")
    if not isMintTime(from_address):
        return
    if value > maxValue:
        print_red("超过最大金额，跳过")
        return
    if to_address in mintadd:
        print_red("mint过，跳过")
        return
    isMint, method = getMethodName(inputData[:10], to_address)
    if not isMint:
        print_red('可能不是mint交易,跳过')
        return
    if not isBlackList(to_address):
        return
    gasPrice, maxFeePerGas, maxPriorityFeePerGas = getgas()
    if gasPrice > maxGasPrice:
        print_red('gasPrice过高,跳过')
        return
    mintadd.append(to_address)
    for index in range(len(accounts)):
        threading.Thread(target=minttx, args=(accounts[index], privateKeys[index], inputData, method, from_address, to_address, maxFeePerGas, maxPriorityFeePerGas, value)).start()


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
    print_red("有能力的请使用源码，不对使用者安全负责")
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
        scanApikey = config['scanApikey']
        blacklist = config['blacklist']
        maxValue = config['maxValue']
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
        w3 = Web3(Web3.HTTPProvider(RPC))
        maxGasPrice = config['maxGasPrice']
        maxGasPrice = w3.toWei(maxGasPrice, 'gwei')
        maxGasLimit = int(config['maxGasLimit'])
        maxValue = w3.toWei(maxValue, 'ether')
        chainId = w3.eth.chainId
        accounts = []
        for privateKey in privateKeys:
            accounts.append(w3.eth.account.privateKeyToAccount(privateKey))
        mintadd = []
        ETHPrice = getETHPrice()
        print('ETH单价: ' + str(ETHPrice))
        methodNameDict = {}
        main()
    except Exception as e:
        print_red(str(e))
        time.sleep(10)
