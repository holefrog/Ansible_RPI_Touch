import time
import spidev
import logging
import numpy as np
import os
from gpiozero import DigitalOutputDevice, PWMOutputDevice

class SmartBacklight:
    """智能背光控制器：绕过 gpiozero，直接驱动内核 sysfs 硬件 PWM"""
    def __init__(self, pin, frequency=1000, initial_value=1.0):
        self.pin = pin
        self._value = initial_value
        self.use_sysfs = False
        
        # BCM GPIO 13 对应底层 pwmchip0 的通道 1 (pwm1)
        if pin == 13:
            self.sysfs_dir = "/sys/class/pwm/pwmchip0/pwm1"
            self.period_ns = int(1e9 / frequency)
            try:
                # 唤醒内核硬件 PWM 接口
                if not os.path.exists(self.sysfs_dir):
                    os.system("sudo sh -c 'echo 1 > /sys/class/pwm/pwmchip0/export'")
                    time.sleep(0.2) # 给内核一点时间生成文件节点
                    
                # 赋予所有用户读写权限，避开非 root 用户的权限墙
                os.system(f"sudo chmod 666 {self.sysfs_dir}/period {self.sysfs_dir}/duty_cycle {self.sysfs_dir}/enable")
                
                # 关键防错：必须先把占空比设为 0，否则新的 period 若小于旧 duty_cycle 会报 Invalid argument
                with open(f"{self.sysfs_dir}/duty_cycle", "w") as f:
                    f.write("0")

                # 配置 1000Hz 周期
                with open(f"{self.sysfs_dir}/period", "w") as f:
                    f.write(str(self.period_ns))
                self.use_sysfs = True
                self.value = initial_value
                # 开启硬件波形发生器
                with open(f"{self.sysfs_dir}/enable", "w") as f:
                    f.write("1")
                logging.info("🚀 纯物理硬件 PWM 已成功接管 GPIO 13，进入绝对零频闪时代！")
            except Exception as e:
                logging.warning(f"⚠️ 硬件 PWM 接口调用受阻 ({e})，回退至防闪烁软件 PWM")
                self.use_sysfs = False
                
        # 权限不足时的安全兜底策略
        if not self.use_sysfs:
            logging.warning("硬件 PWM 初始化失败！回退至 gpiozero 软件 PWM。")
            self.sw_pwm = PWMOutputDevice(pin, frequency=60, initial_value=initial_value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = max(0.0, min(1.0, val))
        if self.use_sysfs:
            try:
                duty_ns = int(self.period_ns * self._value)
                with open(f"{self.sysfs_dir}/duty_cycle", "w") as f:
                    f.write(str(duty_ns))
            except Exception:
                pass
        else:
            self.sw_pwm.value = self._value

SPI_Freq = 24000000     # SPI 时钟频率 (降频至20MHz以提高物理线材连接时的稳定性)
SPI_Mode = 0            # 模式0
RST_PIN  = 27
DC_PIN   = 25
BL_PIN   = 13



class st7796():
    def __init__(self, spi_bus=0, spi_device=0, spi_freq=SPI_Freq, rst_pin=RST_PIN, dc_pin=DC_PIN, bl_pin=BL_PIN, width=320, height=480):
        self.np=np
        self.width  = width
        self.height = height
        
        self.GPIO_RST_PIN = DigitalOutputDevice(rst_pin,active_high = True,initial_value =True)
        self.GPIO_DC_PIN  = DigitalOutputDevice(dc_pin,active_high = True,initial_value =True)
        self.GPIO_BL_PIN  = SmartBacklight(bl_pin, frequency=1000, initial_value=0.0)               # 接入智能纯硬件背光驱动，初始化为0防止花屏
        #Initialize SPI
        self.SPI = spidev.SpiDev(spi_bus, spi_device)
        self.SPI.max_speed_hz = spi_freq  
        self.SPI.mode = 0b00   
        
        # 预分配 Numpy 缓冲区与 memoryview，实现零拷贝 (Zero-Copy) 刷新
        self._pix_landscape = self.np.zeros((self.width, self.height, 2), dtype=self.np.uint8)
        self._mv_landscape = memoryview(self._pix_landscape.reshape(-1))
        
        self._pix_portrait = self.np.zeros((self.height, self.width, 2), dtype=self.np.uint8)
        self._mv_portrait = memoryview(self._pix_portrait.reshape(-1))

        self._current_orientation = "portrait"

        self.lcd_init()
        self.clear()
        self.GPIO_BL_PIN.value = 1.0
    
    def bl_DutyCycle(self, duty):                   # 设置 PWM 占空比
        pass # 已废弃，背光改为常亮

    def digital_write(self, Pin, value):
        if value:
            Pin.on()
        else:
            Pin.off()
            
    def spi_writebyte(self, data):
        if self.SPI!=None :
            self.SPI.writebytes(data)
    
    def command(self, cmd):
        self.digital_write(self.GPIO_DC_PIN, False)
        self.spi_writebyte([cmd])   
        
    def data(self, val):
        self.digital_write(self.GPIO_DC_PIN, True)
        self.spi_writebyte([val])  
        
    def reset(self):
        """Reset the display"""
        self.digital_write(self.GPIO_RST_PIN,True)
        time.sleep(0.01)
        self.digital_write(self.GPIO_RST_PIN,False)
        time.sleep(0.01)
        self.digital_write(self.GPIO_RST_PIN,True)
        time.sleep(0.01)
    
    def dre_rectangle(self, Xstart, Ystart, Xend, Yend, color):
        color_high = (color >> 8) & 0xFF
        color_low = color & 0xFF
            
        self.set_windows( Xstart, Ystart, Xend, Yend) 
        for a in range (Xstart, Xend+1):
            for b in range (Ystart , Yend + 1):
                self.data(color_high)
                self.data(color_low)
    
    def lcd_init(self):
        self.reset()
        self.command(0x11)      
        time.sleep(0.12)

        self.command(0x36)      # Memory Data Access Control MY,MX~~
        self.data(0xC8)    

        self.command(0x3A)      
        self.data(0x05)    # self.data(0x66) 

        self.command(0xF0)      # Command Set Control
        self.data(0xC3)    

        self.command(0xF0)      
        self.data(0x96)    

        self.command(0xB4)      
        self.data(0x01)    

        self.command(0xB7)      
        self.data(0xC6)    

        self.command(0xC0)      
        self.data(0x80)    
        self.data(0x45)    

        self.command(0xC1)      
        self.data(0x13)    # 18  #00

        self.command(0xC2)      
        self.data(0xA7)    

        self.command(0xC5)      
        self.data(0x0A)    

        self.command(0xE8)      
        self.data(0x40) 
        self.data(0x8A) 
        self.data(0x00) 
        self.data(0x00) 
        self.data(0x29) 
        self.data(0x19) 
        self.data(0xA5) 
        self.data(0x33) 

        self.command(0xE0) 
        self.data(0xD0) 
        self.data(0x08) 
        self.data(0x0F) 
        self.data(0x06) 
        self.data(0x06) 
        self.data(0x33) 
        self.data(0x30) 
        self.data(0x33) 
        self.data(0x47) 
        self.data(0x17) 
        self.data(0x13) 
        self.data(0x13) 
        self.data(0x2B) 
        self.data(0x31) 

        self.command(0xE1) 
        self.data(0xD0) 
        self.data(0x0A) 
        self.data(0x11) 
        self.data(0x0B) 
        self.data(0x09) 
        self.data(0x07) 
        self.data(0x2F) 
        self.data(0x33) 
        self.data(0x47) 
        self.data(0x38) 
        self.data(0x15) 
        self.data(0x16) 
        self.data(0x2C) 
        self.data(0x32) 
    
        self.command(0xF0)      
        self.data(0x3C)    

        self.command(0xF0)      
        self.data(0x69)    
        self.command(0x21) # INVON: 必须开启，该IPS屏幕硬件级需要颜色反转

        self.command(0x11)

        time.sleep(0.1)

        self.command(0x29)
        
    def set_windows(self, Xstart, Ystart, Xend, Yend, horizontal = 0):
        if horizontal:  
            #set the X coordinates
            self.command(0x2A)
            self.data(Xstart>>8)         #Set the horizontal starting point to the high octet
            self.data(Xstart & 0xff)     #Set the horizontal starting point to the low octet
            self.data(Xend>>8)         #Set the horizontal end to the high octet
            self.data((Xend) & 0xff)   #Set the horizontal end to the low octet 
            #set the Y coordinates
            self.command(0x2B)
            self.data(Ystart>>8)
            self.data((Ystart & 0xff))
            self.data(Yend>>8)
            self.data((Yend) & 0xff)
            self.command(0x2C)
        else:
            #set the X coordinates
            self.command(0x2A)
            self.data(Xstart>>8)        #Set the horizontal starting point to the high octet
            self.data(Xstart & 0xff)    #Set the horizontal starting point to the low octet
            self.data(Xend>>8)        #Set the horizontal end to the high octet
            self.data((Xend) & 0xff)  #Set the horizontal end to the low octet 
            #set the Y coordinates
            self.command(0x2B)
            self.data(Ystart>>8)
            self.data((Ystart & 0xff))
            self.data(Yend>>8)
            self.data((Yend) & 0xff)
            self.command(0x2C)     
    
    
    def show_image_windows(self, Xstart, Ystart, Xend, Yend, Image):

        # """Set buffer to value of Python Imaging Library image."""
        # """Write display buffer to physical display"""
        imwidth, imheight = Image.size
        if imwidth != self.width or imheight != self.height:
            raise ValueError('Image must be same dimensions as display \
                ({0}x{1}).' .format(self.width, self.height))
        img = self.np.asarray(Image)
        pix = self.np.zeros((imheight,imwidth , 2), dtype = self.np.uint8)
        #RGB888 >> RGB565
        pix[...,[0]] = self.np.add(self.np.bitwise_and(img[...,[0]],0xF8),self.np.right_shift(img[...,[1]],5))
        pix[...,[1]] = self.np.add(self.np.bitwise_and(self.np.left_shift(img[...,[1]],3),0xE0), self.np.right_shift(img[...,[2]],3))
        pix = pix.flatten().tolist()
            
        if Xstart > Xend:
            data = Xstart
            Xstart = Xend
            Xend = data
            
        if Ystart > Yend:        
            data = Ystart
            Ystart = Yend
            Yend = data
        
        if Xend < self.width - 1:
            Xend = Xend + 1
        if Yend < self.width - 1:
            Yend = Yend + 1
            
        self.set_windows( Xstart, Ystart, Xend, Yend)
        self.digital_write(self.GPIO_DC_PIN,True)
        
        for i in range (Ystart,Yend):             
            Addr = ((Xstart) + (i * 240)) * 2        
            self.spi_writebyte(pix[Addr : Addr+((Xend-Xstart+1)*2)])

    def show_image(self, Image):
        """Set buffer to value of Python Imaging Library image."""
        """Write display buffer to physical display"""
        imwidth, imheight = Image.size
        # 如果图片宽度大于高度，则是横屏模式 (Landscape)
        if imwidth > imheight:
            # print("Landscape screen")
            img = self.np.asarray(Image)
            pix = self.np.zeros((imheight, imwidth, 2), dtype = self.np.uint8)
            #RGB888 >> RGB565
            pix[...,[0]] = self.np.add(self.np.bitwise_and(img[...,[0]],0xF8),self.np.right_shift(img[...,[1]],5))
            pix[...,[1]] = self.np.add(self.np.bitwise_and(self.np.left_shift(img[...,[1]],3),0xE0), self.np.right_shift(img[...,[2]],3))
            data = pix.tobytes()
            
            if self._current_orientation != "landscape":
                self.command(0x36)
                self.data(0xE8) # MY=1, MX=1, MV=1, ML=0, BGR=1
                self._current_orientation = "landscape"
                
            self.set_windows(0, 0, imwidth, imheight, 1)
            self.digital_write(self.GPIO_DC_PIN,True)
            for i in range(0, len(data), 4096):
                self.SPI.writebytes2(data[i:i+4096])
        else :
            # print("Portrait screen")
            img = self.np.asarray(Image)
            pix = self.np.zeros((imheight,imwidth , 2), dtype = self.np.uint8)
            
            pix[...,[0]] = self.np.add(self.np.bitwise_and(img[...,[0]],0xF8),self.np.right_shift(img[...,[1]],5))
            pix[...,[1]] = self.np.add(self.np.bitwise_and(self.np.left_shift(img[...,[1]],3),0xE0), self.np.right_shift(img[...,[2]],3))
            data = pix.tobytes()
            
            if self._current_orientation != "portrait":
                self.command(0x36)
                self.data(0xC8) # MY=1, MX=1, MV=0, ML=0, BGR=1
                self._current_orientation = "portrait"
                
            self.set_windows(0, 0, imwidth, imheight, 0)
            self.digital_write(self.GPIO_DC_PIN,True)
            for i in range(0, len(data), 4096):
                self.SPI.writebytes2(data[i:i+4096])
                
    def show_image_partial(self, Image, x, y):
        """局部刷新：只传输画面发生变化的部分，突破 SPI 瓶颈实现极高帧率"""
        imwidth, imheight = Image.size
        if imwidth == 0 or imheight == 0:
            return
            
        img = self.np.asarray(Image)
        pix = self.np.zeros((imheight, imwidth, 2), dtype=self.np.uint8)
        
        # RGB888 >> RGB565
        pix[...,[0]] = self.np.add(self.np.bitwise_and(img[...,[0]],0xF8),self.np.right_shift(img[...,[1]],5))
        pix[...,[1]] = self.np.add(self.np.bitwise_and(self.np.left_shift(img[...,[1]],3),0xE0), self.np.right_shift(img[...,[2]],3))
        data = pix.tobytes()
        
        if self._current_orientation != "landscape":
            self.command(0x36)
            self.data(0xE8) # MY=1, MX=1, MV=1, ML=0, BGR=1
            self._current_orientation = "landscape"
            
        # 精准定点写入 SPI 显存
        self.set_windows(x, y, x + imwidth - 1, y + imheight - 1, 1)
        self.digital_write(self.GPIO_DC_PIN, True)
        for i in range(0, len(data), 4096):
            self.SPI.writebytes2(data[i:i+4096])

    
    def clear(self):
        """Clear contents of image buffer (fill with black)"""
        # b'\x00' 在 RGB565 中代表黑色 (原先的 b'\xff' 代表白色)
        _buffer = b'\x00' * (self.width * self.height * 2)
        
        # 动态适配当前屏幕的横竖屏状态，以防刷错尺寸
        if self._current_orientation == "landscape":
            self.set_windows(0, 0, self.height, self.width, 1)
        else:
            self.set_windows(0, 0, self.width, self.height, 0)
            
        self.digital_write(self.GPIO_DC_PIN,True)
        for i in range(0, len(_buffer), 4096):
            self.SPI.writebytes2(_buffer[i: i+4096])
