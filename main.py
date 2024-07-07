from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.uic import loadUi

import os, sys, datetime, time, search

os.environ['BASE_DIR'] = os.getcwd()
BASE_DIR = os.getenv('BASE_DIR')


class VillaSearchThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, parameters, loading_movie: QMovie, loading_label: QLabel, ):
        super(VillaSearchThread, self).__init__()
        self.parameters = parameters

    def run(self):
        # Burada villa arama işlemi yapılır.
        # Bu örnekte, zaman uyutma kullanılarak işlem taklit edilmektedir.
        self.loading_movie.start()
        search.search_all(self.parameters)
        villas = ["Villa Sunshine", "Villa Sea Breeze", "Mountain View Villa", "Villa Oceanfront", "Countryside Villa", "Urban Villa"]
        self.finished.emit(villas)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi(os.path.join(BASE_DIR, 'mainwindow.ui'), self)
        
        self.st_index = 0
        self.last_clicked_item = QListWidgetItem()
        self.villas = list()
        self.one_cikarilan_items = list()        
        self.bolgelerDict = {}
        self.ozelliklerDict = {}
        with open(os.path.join(BASE_DIR, "bolgeler.csv"), "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
            for line in lines:
                name, code = line.split(",")
                self.bolgelerDict.update({name: code})
        with open(os.path.join(BASE_DIR, "ozellikler.csv"), "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
            for line in lines:
                name, code = line.split(",")
                self.ozelliklerDict.update({name: code})

        self.check_licence()
        self.set_ui()
        self.set_signals()
        self.set_window_settings()
        
    def check_licence(self): 
        if True:
            return True
        else:
            sys.exit()
            
    def set_ui(self):
        # Frames
        self.result_frame.hide()
        today = datetime.date.today()
        today = QDate(today.year, today.month, today.day)
        self.checkin_dateedit.setDate(today)
        self.checkout_dateedit.setDate(today)

        # -> List Widgets
        # Bölgeler
        with open(os.path.join(BASE_DIR, "bolgeler"), "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
            lines.sort()
            self.bolgeler = dict()
            self.bolge_items = list()
            for line in lines:
                ad, kod = line.split(",")
                self.bolgeler.update({ad: kod})
                item = QListWidgetItem(ad, self.bolgeler_widget)
                item.setCheckState(Qt.Unchecked)
                
                self.bolgeler_widget.addItem(item)
                self.bolge_items.append(item)
                
        # Özellikler
        with open(os.path.join(BASE_DIR, "ozellikler"), "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
            lines.sort()
            self.ozellikler = dict()
            self.ozellik_items = list()
            for line in lines:
                ad, kod = line.split(",")
                self.ozellikler.update({ad: kod})
                item = QListWidgetItem(ad, self.ozellikler_widget)
                item.setCheckState(Qt.Unchecked)
                
                self.ozellikler_widget.addItem(item)
                self.ozellik_items.append(item)
        
        # Yükleniyor animasyonu
        self.loading_label = QLabel(self)
        self.loading_movie = QMovie("loading.gif")
        self.loading_label.setMovie(self.loading_movie)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.hide()
        self.main_layout.addWidget(self.loading_label)
        
        # Seçilen villaların gösterileceği liste - self.selected_villas
        self.selected_villas.setSelectionMode(QListWidget.NoSelection)
        self.selected_villas.mousePressEvent = self.on_villa_item_click
        
    def set_signals(self):
        self.previous_btn.clicked.connect(self.st_prev_btn_clicked)
        self.next_btn.clicked.connect(self.st_next_btn_clicked)

        # -> Search Tab Widgets
        self.bolgeler_widget.itemClicked.connect(lambda item: self.st_item_clicked(item))
        self.ozellikler_widget.itemClicked.connect(lambda item: self.st_item_clicked(item))
        
        self.select_all1.clicked.connect(lambda: self.change_state(self.bolge_items, Qt.Checked))
        self.select_all2.clicked.connect(lambda: self.change_state(self.ozellik_items, Qt.Checked))
        self.deselect_all1.clicked.connect(lambda: self.change_state(self.bolge_items, Qt.Unchecked))
        self.deselect_all2.clicked.connect(lambda: self.change_state(self.ozellik_items, Qt.Unchecked))

        self.search_button.clicked.connect(self.start_search)

    def start_search(self):
        date_ranges = [self.checkin_dateedit.date().toPyDate()]
        nights_before = self.nights_before_spin.value()
        nights_after = self.nights_afters_spin.value()
        parent = str(self.parentcount.value())
        child = self.childcount.value()
        features = []
        areas = []
        parameters = {
            'date-ranges': date_ranges,
            'nights-nefore': nights_before,
            'night-after': nights_after,
            'parent': parent,
            'child': child,
            'features': features,
            'areas': areas,
        }   
        
        # Villa arama işlemi için thread
        self.search_thread = VillaSearchThread()
        self.search_thread.finished.connect(self.on_search_finished)
        
        self.search_frame.hide()
        self.next_btn.hide()
        self.previous_btn.hide()
        self.loading_label.show()
        self.loading_movie.start()
        self.search_thread.start()
    
    def on_search_finished(self, villas):
        self.villas = villas
        self.loading_movie.stop()
        self.loading_label.hide()
        self.result_frame.show()
        self.previous_btn.show()
        self.st_index = 1

        # QCompleter oluştur
        self.completer = QCompleter(self.villas, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.search_box.setCompleter(self.completer)
        
        # QCompleter'daki öğeye tıklanınca öğeyi seçilen villalar listesine ekle
        self.completer.activated.connect(self.add_selected_villa)
        
    def st_prev_btn_clicked(self):
        if self.st_index:
            self.result_frame.hide()
            self.search_frame.show()
            self.st_index = 0
            self.previous_btn.hide()
            self.next_btn.show()
            
    def st_next_btn_clicked(self):
        if not self.st_index:
            self.search_frame.hide()
            self.result_frame.show()
            self.st_index = 1
            self.next_btn.hide()
            self.previous_btn.show()
            
    def st_item_clicked(self, item: QListWidgetItem):
        if not item.checkState():
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)
        self.last_clicked_item = item

    def on_villa_item_click(self, event):
        # Tiklanan ogeyi bul ve sil
        item = self.selected_villas.itemAt(event.pos())
        if item:
            self.selected_villas.takeItem(self.selected_villas.row(item))

    def change_state(self, items, stateTo):
        for item in items:
            item.setCheckState(stateTo)
        self.last_clicked_item.setSelected(False)
        self.last_clicked_item = QListWidgetItem()
    
    def add_selected_villa(self, text):
        item = QListWidgetItem(text)
        self.one_cikarilan_items.append(item)
        self.selected_villas.addItem(item)
        self.search_box.clear()
        
        self.update_text()

    def update_text(self):
        pass
    
    def set_window_settings(self):
        self.setWindowTitle("Project Alpha | EKLENTI PAKETI")
        self.setWindowIcon(QIcon(os.path.join(BASE_DIR, 'window_icon.png')))
        self.show()
        
app = QApplication(sys.argv)
window = MainWindow()
sys.exit(app.exec_())