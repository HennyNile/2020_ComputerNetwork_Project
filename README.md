# 2020_ComputerNetwork_Project
OS: WINDOWS 10  
Python version: 3.8.3  

1.由于实现问题，客户端和测试端的端口需要在建立连接前绑定，否则会报错！  
2.rdt协议的检测超时的标准timeout有初始化值，为RDTSocket的初始化方法__init__()中的self.timeout, 第一、二种测试由于单个连接，同时传输的包较少，因此设为1既可以取得较快的速率也可以保证正常传输不会超时；第二三种测试由于同时传输的包很多，若timeout很小，就会仅仅因为等待队列较长就导致重传，所以timeout需要长一些，经过测试timeout=3时，效果最好。为了满足所有的测试需要，timeout当前设置为3， 这导致第一二种的传输效率会慢很多。
