from Mainwindow.common import *

from Mainwindow.MainWindow import MainWindow

class AppManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = None
        self._have_main_window = False
        self.init_platform_style()
        self.setup_logging()

    def init_platform_style(self):
        self.app.setStyle('Fusion')

        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)

        self.app.setPalette(dark_palette)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

    def show_main_window(self):
        if not self._have_main_window:
            self.main_window = MainWindow(self.app, 2000, 1250)
            self._have_main_window = True

        self.main_window.show()
        self.main_window.setWindowState(
            self.main_window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive
        )
        self.main_window.raise_()
        self.main_window.activateWindow()

    def run(self):
        self.show_main_window()
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    manager = AppManager()
    manager.run()