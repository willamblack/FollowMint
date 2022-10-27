# 需要的module
web3，requests


# FollowMint

选一个狗王，跟着狗王，狗王mint啥软件自动帮你mint啥

已经自动排除非mint交易，非免费交易，已做模拟交易，模拟成功的才发送


编辑config.json里的参数：

**RPC**：ETH节点RPC

**privateKey**：私钥数组["私钥1", "私钥2"]，有几个号加几个

**blocknativeKey**：https://www.blocknative.com/  创建个账号，个人中心获取，不需要设置，直接复制key即可，和alchemyKey二选一，用哪个填哪个，不填置”“

**alchemyKey**：https://www.alchemy.com/ 创建ETH项目，获取，这个也是用于监控，和blocknative二选一，用哪个填哪个，不填置”“

**barkKey**：IOS的bark软件推送key，用于推送mint成功或者失败信息（没有可以空着）

**scanApikey**：https://etherscan.io/register 区块浏览器注册获取

**maxGasPrice**：最大的GAS，超过不会跟

**maxGasLimit**：最大的GAS消耗，超过不会跟

**maxValue**: 最大金额（设置0就只跟免费的，0.1就表示收费0.1以下的也跟）

**follow**：需要跟随的狗王地址，"follow": {"狗王地址":{"start": 开始跟单时间, "end": 结束跟单时间}}

**blacklist**：土狗名字黑名单，含有这些词的屏蔽

# 报错
1，async for' requires an object with __aiter__ method

  pip install websockets==10.3更新下websockets既可

2，handshake failed

  网络连接不上blocknative，尝试更换alchemy试试


# 已打包的exe
自行打包或者找朋友帮忙pyinstaller打包吧

实在要用exe的进discord下载吧

直接提示错误的，应该是配置文件错误

# 推特
https://twitter.com/fooyao158

# Discord

https://discord.gg/mgrcUfPEF9

# 打赏

fooyao.eth

