"""
创建小猫图片资源
运行此脚本生成小猫图片
"""
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QFont
from PyQt5.QtCore import Qt, QRectF
import os

def create_cat_image():
    """创建简单的小猫图片"""
    # 创建400x400透明背景的图片
    pixmap = QPixmap(400, 400)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # 猫身体（浅粉色圆形）
    painter.setBrush(QBrush(QColor(255, 182, 193)))  # 浅粉色
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(150, 150, 100, 100)
    
    # 猫耳朵
    painter.setBrush(QBrush(QColor(255, 182, 193)))
    # 左耳
    painter.drawEllipse(130, 130, 40, 50)
    # 右耳
    painter.drawEllipse(230, 130, 40, 50)
    
    # 内耳（深粉色）
    painter.setBrush(QBrush(QColor(255, 150, 170)))
    painter.drawEllipse(140, 140, 20, 30)
    painter.drawEllipse(240, 140, 20, 30)
    
    # 眼睛（黑色圆形）
    painter.setBrush(QBrush(QColor(0, 0, 0)))
    painter.drawEllipse(170, 170, 15, 15)
    painter.drawEllipse(215, 170, 15, 15)
    
    # 眼睛高光（白色）
    painter.setBrush(QBrush(QColor(255, 255, 255)))
    painter.drawEllipse(173, 173, 5, 5)
    painter.drawEllipse(218, 173, 5, 5)
    
    # 鼻子（粉色小圆）
    painter.setBrush(QBrush(QColor(255, 100, 130)))
    painter.drawEllipse(192, 190, 16, 12)
    
    # 嘴巴（微笑弧线）
    painter.setPen(QPen(QColor(0, 0, 0), 2))
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(180, 195, 20, 15, 0, 180 * 16)
    painter.drawArc(200, 195, 20, 15, 0, 180 * 16)
    
    # 胡须
    painter.setPen(QPen(QColor(100, 100, 100), 1.5))
    painter.drawLine(150, 195, 120, 190)
    painter.drawLine(150, 200, 120, 205)
    painter.drawLine(250, 195, 280, 190)
    painter.drawLine(250, 200, 280, 205)
    
    painter.end()
    
    return pixmap

def save_cat_image():
    """保存小猫图片到应用目录"""
    # 获取当前文件目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建app_data目录
    app_data_dir = os.path.join(current_dir, "app_data")
    if not os.path.exists(app_data_dir):
        os.makedirs(app_data_dir)
    
    # 保存图片
    cat_path = os.path.join(app_data_dir, "cat.png")
    pixmap = create_cat_image()
    pixmap.save(cat_path, "PNG")
    
    print(f"[CatImage] 小猫图片已保存到: {cat_path}")
    return cat_path

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    path = save_cat_image()
    print(f"图片路径: {path}")
