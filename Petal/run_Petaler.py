# -*- coding: utf-8 -*-
"""
Petal 桌面宠物应用启动脚本。

该脚本负责加载宠物数据，初始化 PyQt5 应用，
应用自定义样式表，并创建和显示主宠物窗口 (PetWidget)。
"""

import sys
import threading
import time

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from Petal.Petaler import PetWidget
from Petal.utils import read_json



STYLE_SHEET = '''
#PetHP {
    border: 2px solid #535053;
    border-radius: 7px;
}
#PetHP::chunk {
    background-color: #f44357;
    border-radius: 5px;
}

#PetEM {
    border: 2px solid #535053;
    border-radius: 7px;
}
#PetEM::chunk {
    background-color: #f6ce5f;
    border-radius: 5px;
}

#PetFC {
    border: 2px solid #535053;
    border-radius: 7px;
}
#PetFC::chunk {
    background-color: #47c0d2;
    border-radius: 5px;
}
'''


STYLE_SHEET = '''
#PetHP {
    border: 2px solid #535053;
    border-radius: 7px;
}
#PetHP::chunk {
    background-color: #f44357;
    border-radius: 5px;
}

#PetEM {
    border: 2px solid #535053;
    border-radius: 7px;
}
#PetEM::chunk {
    background-color: #f6ce5f;
    border-radius: 5px;
}

#PetFC {
    border: 2px solid #535053;
    border-radius: 7px;
}
#PetFC::chunk {
    background-color: #47c0d2;
    border-radius: 5px;
}
'''

def create_pet_widget(pets_json_path, curr_pet_name: str = ''):
    try:
        pets_data = read_json(pets_json_path)
        print(f"{pets_json_path} 加载成功。")
    except Exception as e:
        print(f"{pets_json_path} 加载失败: {e}")
        return None

    pet = PetWidget(pets=pets_data, curr_pet_name = curr_pet_name)
    pet.show()
    print(f"{pets_json_path} 宠物窗口创建完成。")
    return pet


if __name__ == '__main__':
    print("主程序启动。")
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)

    # 创建第一个宠物窗口
    pet1 = create_pet_widget('data/pets.json')

    QTimer.singleShot(5000, lambda: create_pet_widget('data/pets.json'))

    QTimer.singleShot(10000, lambda: create_pet_widget('data/pets.json'))

    print("进入事件循环。")
    sys.exit(app.exec_())



