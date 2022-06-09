import os
import json
import time
import asyncio
import platform
import requests
import threading
import websockets
from web3 import Web3
from datetime import datetime
from eth_abi import decode_abi

configExample = {
    "RPC": "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161",
    "privateKey": ["privateKey1", "privateKey2"],
    "blocknativeKey": "",
    "alchemyKey": "",
    "barkKey": "",
    "scanApikey": "",
    "maxGasPrice": 50,
    "maxGasLimit": 1000000,
    "maxValue": 0,
    "maxMintNum": 5,
    "follow": {
        "0x8888887a5e2491fec904d90044e6cd6c69f1e71c": {"start": 0, "end": 24},
        "0x555555B63d1C3A8c09FB109d2c80464685Ee042B": {"start": 18, "end": 6},
        "0x99999983c70de9543cdc11dB5DE66A457d241e8B": {"start": 8, "end": 20}
    },
    "blacklist": ["Ape", "Pixel", "Not", "Okay", "Woman", "Baby", "Goblin", "Ai"]
}

if platform.system().lower() == 'windows':
    import ctypes
    import sys

    std_out_handle = ctypes.windll.kernel32.GetStdHandle(-11)


    def set_cmd_text_color(color, handle=std_out_handle):
        Bool = ctypes.windll.kernel32.SetConsoleTextAttribute(handle, color)
        return Bool


    def print_color(message, color):
        colorDict = {'green': 0x0a, 'red': 0x0c, 'blue': 0x0b, 'yellow': 0x0e}
        stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
        set_cmd_text_color(colorDict[color])
        sys.stdout.write(f'[{stime}] {message}\n')
        set_cmd_text_color(0x0c | 0x0a | 0x09)
else:
    def print_color(message, color):
        colorDict = {'green': '32m', 'red': '31m', 'blue': '34m', 'yellow': '33m'}
        stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
        print(f'[{stime}] \033[1;{colorDict[color]}{message}\033[0m')


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


def getMethodName(methodSignature, _conadd, _pendingBlockNumber):
    try:
        isMint, mintNum = isMintFromBlock(_pendingBlockNumber, _conadd, methodSignature)
        if isMint:
            if methodSignature in methodNameDict:
                print_color('mint方法：' + methodNameDict[methodSignature]['method'], 'blue')
                return methodNameDict[methodSignature]['isMint'], methodNameDict[methodSignature]['method'], mintNum
            res = requests.get('https://www.4byte.directory/api/v1/signatures/?hex_signature=' + methodSignature)
            if res.status_code == 200 and res.json()['count'] > 0:
                method = res.json()['results'][0]['text_signature']
                print_color('mint方法：' + method, 'blue')
                methodNameDict[methodSignature] = {'method': method, 'isMint': True}
                return True, method, mintNum
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
                    print_color('mint方法：' + method, 'blue')
                    methodNameDict[methodSignature] = {'method': method, 'isMint': True}
                    return True, method, mintNum
        else:
            return False, None, 0
    except:
        return False, None, 0


def isMintFromBlock(_block, _conadd, _methodSignature):
    try:
        log = w3.eth.filter({
            'fromBlock': _block - 11,
            'toBlock': _block - 1,
            'address': w3.toChecksumAddress(_conadd),
            'topics': ['0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
                       '0x0000000000000000000000000000000000000000000000000000000000000000']
        })
        txs = log.get_all_entries()
        if len(txs) > 1:
            transactionHashList = [tx.transactionHash for tx in txs]
            allMaxMint = transactionHashList.count(max(transactionHashList, key=transactionHashList.count))
            transaction = w3.eth.get_transaction(txs[0]['transactionHash'])
            mintMethod = transaction['input'][:10]
            if _methodSignature == mintMethod:
                return True, allMaxMint
    except Exception as e:
        print(str(e))
    return False, 0


def isBlackList(_to):
    try:
        NFTcon = w3.eth.contract(address=_to, abi=[nameabi])
        name = NFTcon.functions.name().call()
        for black in blacklist:
            if black in name:
                print_color(name + "黑名单" + black + "，跳过", 'red')
                return False
    except:
        print_color('获取NFT名称失败，跳过', 'red')
        return False
    print_color('NFT名称：' + name, 'blue')
    return True


def isMintTime(_from):
    if _from.lower() in follows:
        starttime = int(follows[_from.lower()]['start'])
        endtime = int(follows[_from.lower()]['end'])
        tm_hour = time.localtime().tm_hour
        if starttime < endtime:
            if starttime <= tm_hour < endtime:
                pass
            else:
                print_color("非Mint时间，跳过", 'red')
                return False
        else:
            if endtime <= tm_hour < starttime:
                print_color("非Mint时间，跳过", 'red')
                return False
            else:
                pass
    return True


def getgas():
    url = 'https://blocknative-api.herokuapp.com/data'
    res = requests.get(url=url)
    if res.status_code == 200:
        estimatedPrices = res.json()['estimatedPrices'][0]
        maxPriorityFeePerGas = estimatedPrices['maxPriorityFeePerGas']
        maxFeePerGas = estimatedPrices['maxFeePerGas']
        baseFee = estimatedPrices['price']
        maxPriorityFeePerGas = w3.toWei(maxPriorityFeePerGas + 0.1, 'gwei')
        maxFeePerGas = w3.toWei(maxFeePerGas + 0.1, 'gwei')
        baseFee = w3.toWei(baseFee + 0.1, 'gwei')
        return baseFee, maxFeePerGas, maxPriorityFeePerGas


def minttx(_account, _privateKey, _inputData, _method, _from_address, _to_address, _maxFeePerGas, _maxPriorityFeePerGas, _value, _gasLimit):
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
            'gas': _gasLimit,
            'maxFeePerGas': int(_maxFeePerGas * 2),
            'maxPriorityFeePerGas': _maxPriorityFeePerGas,
            'nonce': w3.eth.getTransactionCount(_account.address),
            'data': _inputData,
            'value': _value
        }
        try:
            estimateGas = w3.eth.estimateGas(transaction)
            if estimateGas > _gasLimit:
                transaction['gas'] = int(estimateGas * 1.2)
        except Exception as e:
            if 'max fee per gas less than block base fee' in str(e):
                _, maxFeePerGas, maxPriorityFeePerGas = getgas()
                transaction['maxFeePerGas'] = int(maxFeePerGas * 2)
                transaction['maxPriorityFeePerGas'] = maxPriorityFeePerGas
            elif 'allowance' not in str(e):
                print_color('发送交易失败:' + str(e), 'red')
                if _to_address in mintadd:
                    mintadd.remove(_to_address)
                return
        signed = w3.eth.account.sign_transaction(transaction, _privateKey)
        new_raw = signed.rawTransaction.hex()
        tx_hash = w3.eth.sendRawTransaction(new_raw)
        print_color("mint交易发送成功" + w3.toHex(tx_hash), 'green')
        freceipt = w3.eth.waitForTransactionReceipt(tx_hash, 600)
        if freceipt.status == 1:
            try:
                ETHused = freceipt.effectiveGasPrice * freceipt.gasUsed
                ETHused = float(w3.fromWei(ETHused, 'ether'))
                USDuse = ETHPrice * ETHused
                ETHusedinfo = '本次mint：' + str(USDuse) + ' U'
            except:
                ETHusedinfo = ''
            print_color("mint成功   " + ETHusedinfo, 'green')
            bark('mint成功', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
        else:
            print_color("mint失败", 'red')
            if _to_address in mintadd:
                mintadd.remove(_to_address)
            bark('mint失败', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
    except Exception as e:
        if _to_address in mintadd:
            mintadd.remove(_to_address)
        print_color('交易失败:' + str(e), 'red')
        return


def txn_handler(to_address, from_address, inputData, value, gasLimit, tx_maxFeePerGas, tx_maxPriorityFeePerGas, pendingBlockNumber):
    to_address = w3.toChecksumAddress(to_address)
    print_color(from_address + "监控到新交易", 'yellow')
    if not isMintTime(from_address):
        return
    if value > maxValue:
        print_color("超过最大金额，跳过", 'red')
        return
    if to_address in mintadd:
        print_color("mint过，跳过", 'red')
        return
    isMint, method, mintNum = getMethodName(inputData[:10], to_address, pendingBlockNumber)
    if not isMint:
        print_color('可能不是mint交易,跳过', 'red')
        return
    if mintNum > maxMintNum:
        print_color(f'mint数量{mintNum}超过设定上限{maxMintNum},跳过', 'red')
        return
    if not isBlackList(to_address):
        return
    gasPrice, maxFeePerGas, maxPriorityFeePerGas = getgas()
    if gasPrice > maxGasPrice:
        print_color('gasPrice过高,跳过', 'red')
        return
    maxFeePerGas = maxFeePerGas if maxFeePerGas > tx_maxFeePerGas else tx_maxFeePerGas
    maxPriorityFeePerGas = maxPriorityFeePerGas if maxPriorityFeePerGas > tx_maxPriorityFeePerGas else tx_maxPriorityFeePerGas
    if gasPrice + maxPriorityFeePerGas < maxFeePerGas:
        maxFeePerGas = gasPrice + maxPriorityFeePerGas
    mintadd.append(to_address)
    for index in range(len(accounts)):
        threading.Thread(target=minttx, args=(accounts[index], privateKeys[index], inputData, method, from_address, to_address, maxFeePerGas, maxPriorityFeePerGas, value, gasLimit)).start()


async def blocknative():
    async for websocket in websockets.connect('wss://api.blocknative.com/v0'):
        try:
            initialize = {
                "categoryCode": "initialize",
                "eventCode": "checkDappId",
                "dappId": blocknativeKey,
                "timeStamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                "version": "1",
                "blockchain": {
                    "system": "ethereum",
                    "network": "main"
                }
            }
            await websocket.send(json.dumps(initialize))
            for _follow in follows:
                configs = {
                    "categoryCode": "configs",
                    "eventCode": "put",
                    "config": {
                        "scope": _follow,
                        "filters": [
                            {
                                "from": _follow,
                                "status": "pending"
                            }
                        ],
                        "watchAddress": True
                    },
                    "dappId": blocknativeKey,
                    "timeStamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                    "version": "1",
                    "blockchain": {
                        "system": "ethereum",
                        "network": "main"
                    }
                }
                await websocket.send(json.dumps(configs))
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30*60)
                except asyncio.TimeoutError:
                    print_color('30分钟无消息，可能断开，尝试重连', 'red')
                    await websocket.close()
                    break
                json_data = json.loads(message)
                if json_data['status'] == 'ok' and 'event' in json_data:
                    if json_data['event']['categoryCode'] == 'initialize':
                        print_color('初始化成功', 'blue')
                    elif json_data['event']['categoryCode'] == 'configs':
                        print_color(f"监控{json_data['event']['config']['scope']}地址成功", 'blue')
                    elif json_data['event']['categoryCode'] == 'activeAddress':
                        txn = json_data['event']['transaction']
                        to_address = txn['to']
                        from_address = txn['from']
                        inputData = txn['input']
                        gasLimit = int(txn['gas'])
                        value = int(txn['value'])
                        if 'maxFeePerGas' in txn:
                            tx_maxFeePerGas = int(txn['maxFeePerGas'])
                            tx_maxPriorityFeePerGas = int(txn['maxPriorityFeePerGas'])
                        else:
                            tx_maxFeePerGas, tx_maxPriorityFeePerGas = 0, 0
                        pendingBlockNumber = int(txn['pendingBlockNumber'])
                        threading.Thread(target=txn_handler, args=(to_address, from_address, inputData, value, gasLimit, tx_maxFeePerGas, tx_maxPriorityFeePerGas, pendingBlockNumber)).start()
                    else:
                        print_color(message, 'blue')
        except Exception as e:
            print_color(str(e), 'red')
            await websocket.close()


async def alchemy():
    async for websocket in websockets.connect(f'wss://eth-mainnet.alchemyapi.io/v2/{alchemyKey}'):
        try:
            json_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": []
            }
            for _follow in follows:
                json_data['params'] = ["alchemy_filteredNewFullPendingTransactions", {"address": _follow}]
                await websocket.send(json.dumps(json_data))
                result = await websocket.recv()
                if "result" in result:
                    print_color(f"监控{_follow}地址成功", 'blue')
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30*60)
                except asyncio.TimeoutError:
                    print_color('30分钟无消息，可能断开，尝试重连', 'red')
                    await websocket.close()
                    break
                json_data = json.loads(message)
                if 'params' in json_data:
                    txn = json_data['params']['result']
                    to_address = txn['to']
                    from_address = txn['from']
                    if from_address.lower() not in follows:
                        return
                    inputData = txn['input']
                    gasLimit = int(txn['gas'], 16)
                    value = int(txn['value'], 16)
                    if 'maxFeePerGas' in txn:
                        tx_maxFeePerGas = int(txn['maxFeePerGas'], 16)
                        tx_maxPriorityFeePerGas = int(txn['maxPriorityFeePerGas'], 16)
                    else:
                        tx_maxFeePerGas, tx_maxPriorityFeePerGas = 0, 0
                    pendingBlockNumber = w3.eth.get_block_number()
                    threading.Thread(target=txn_handler, args=(to_address, from_address, inputData, value, gasLimit, tx_maxFeePerGas, tx_maxPriorityFeePerGas, pendingBlockNumber)).start()
        except Exception as e:
            print_color(str(e), 'red')
            await websocket.close()


if __name__ == '__main__':
    print_color("有能力的请使用源码，不对使用者安全负责", 'red')
    print_color("打狗请用小号，无法保证无bug", 'red')
    print_color("开源地址：https://github.com/Fooyao/FollowMint", 'red')
    print_color("代码水平较差，有任何优化建议请反馈", 'red')
    if not os.path.exists('config.json'):
        print_color('请先配置config.json', 'blue')
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
        alchemyKey = config['alchemyKey']
        barkKey = config['barkKey']
        follows = config['follow']
        maxMintNum = int(config['maxMintNum'])
        follows = dict((k.lower(), v) for k, v in follows.items())
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
        accounts = [w3.eth.account.privateKeyToAccount(privateKey) for privateKey in privateKeys]
        mintadd = []
        ETHPrice = getETHPrice()
        print_color('ETH单价: ' + str(ETHPrice), 'green')
        methodNameDict = {
            '0xab834bab': {'method': 'atomicMatch_', 'isMint': False},
            '0xa22cb465': {'method': 'setApprovalForAll', 'isMint': False},
            '0x23b872dd': {'method': 'transferFrom', 'isMint': False},
            '0xa8a41c70': {'method': 'cancelOrder_', 'isMint': False}
        }
        if len(blocknativeKey) >= 20:
            asyncio.run(blocknative())
        elif len(alchemyKey) >= 20:
            asyncio.run(alchemy())
        else:
            print_color('blocknativeKey和alchemyKey必须提供一个', 'red')
    except Exception as e:
        print_color(str(e), 'red')
        time.sleep(10)
