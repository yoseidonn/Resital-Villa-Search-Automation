from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.uic import loadUi

import os, sys, datetime, time, search, pyperclip

os.environ['BASE_DIR'] = os.getcwd()
BASE_DIR = os.getenv('BASE_DIR')


class VillaSearchThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, parameters):
        super(VillaSearchThread, self).__init__()
        self.parameters = parameters
        
    def run(self):
        # Burada villa arama işlemi yapılır.
        # Bu örnekte, zaman uyutma kullanılarak işlem taklit edilmektedir.
        result = search.search_villas(self.parameters)
        self.finished.emit(result)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi(os.path.join(BASE_DIR, 'static', 'ui', 'mainwindow.ui'), self)
        
        self.st_index = 0
        self.last_clicked_item = QListWidgetItem()
        self.infos_text = ''
        self.villas = list()
        self.one_cikarilan_items = list()        
        self.one_cikarilan_names = list()
        self.bolgelerDict = {}
        self.ozelliklerDict = {}
        with open(os.path.join(BASE_DIR, 'static', 'csv', 'bolgeler.csv'), 'r', encoding='utf-8') as f:
            lines = f.read().split("\n")
            for line in lines:
                name, code = line.split(",")
                self.bolgelerDict.update({name: code})
        with open(os.path.join(BASE_DIR, 'static', 'csv', 'ozellikler.csv'), 'r', encoding='utf-8') as f:
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
        self.ranges_in_range_frame.hide()
        self.result_frame.hide()
        today = datetime.date.today()
        today = QDate(today.year, today.month, today.day)
        self.checkin_de.setDate(today)
        self.checkout_de.setDate(today)
        self.parent_range_start_de.setDate(today)
        self.parent_range_end_de.setDate(today)

        
        # -> List Widgets
        # Bölgeler
        with open(os.path.join(BASE_DIR, 'static', 'csv', 'bolgeler.csv'), 'r', encoding='utf-8') as f:
            lines = f.read().split("\n")
            lines.sort()
            self.bolge_items = list()
            for line in lines:
                ad, kod = line.split(",")
                item = QListWidgetItem(ad, self.bolgeler_widget)
                item.setCheckState(Qt.Unchecked)
                
                self.bolgeler_widget.addItem(item)
                self.bolge_items.append(item)
                
        # Özellikler
        with open(os.path.join(BASE_DIR, 'static', 'csv', 'ozellikler.csv'), 'r', encoding='utf-8') as f:
            lines = f.read().split("\n")
            lines.sort()
            self.ozellik_items = list()
            for line in lines:
                ad, kod = line.split(",")
                item = QListWidgetItem(ad, self.ozellikler_widget)
                item.setCheckState(Qt.Unchecked)
                
                self.ozellikler_widget.addItem(item)
                self.ozellik_items.append(item)
        
        # Yükleniyor animasyonu
        self.loading_label = QLabel(self)
        self.loading_movie = QMovie(os.path.join(BASE_DIR, 'static', 'gif', 'loading.gif'))
        self.loading_label.setMovie(self.loading_movie)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setGeometry(0, 0, self.width(), self.height())
        self.loading_movie.setScaledSize(QSize(self.width(), self.height()))
        self.loading_label.hide()
        self.main_layout.addWidget(self.loading_label)
        
        # Seçilen villaların gösterileceği liste - self.selected_villas
        self.selected_villas.setSelectionMode(QListWidget.NoSelection)
        self.selected_villas.mousePressEvent = self.on_villa_item_click
        self.selected_villas.setDragEnabled(True)
        self.selected_villas.setAcceptDrops(True)
        self.selected_villas.setDragDropMode(QAbstractItemView.InternalMove)

        
    def set_signals(self):
        self.ranges_in_range_cb.stateChanged.connect(self.rib_cb_changed)
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
        self.copy_button.clicked.connect(self.copy_infos)

    def start_search(self):
        holiday_range = str(self.checkin_de.date().toPyDate()) + '_' + str(self.checkout_de.date().toPyDate())
        nights_before = self.nights_before_spin.value()
        nights_after = self.nights_after_spin.value()
        parent = str(self.parentcount.value())
        child = self.childcount.value()
        features = []
        areas = []
        for item in self.bolge_items:
            if item.checkState():
                areas.append(self.bolgelerDict[item.text()])
        for item in self.ozellik_items:
            if item.checkState():
                features.append(self.ozelliklerDict[item.text()])
        if not areas:
            areas.append("0")
        if not features:
            features.append("0")
            
        parameters = {
            'ranges_in_range': self.ranges_in_range_cb,
            'parent-range-start': str(),
            'parent-range-end': str(),
            'child-range-lenghts': list[int],
            'holiday-range': holiday_range,
            'nights-nefore': nights_before,
            'night-after': nights_after,
            'parent': parent,
            'child': child,
            'features': features,
            'areas': areas,
        }   
        
        # Villa arama işlemi için thread
        self.search_thread = VillaSearchThread(parameters)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_frame.hide()
        self.next_btn.hide()
        self.previous_btn.hide()
        self.loading_label.show()
        self.loading_movie.start()
        self.search_thread.start()
    
    def on_search_finished(self, result: dict):
        self.villa_dicts = result
        self.loading_movie.stop()
        self.loading_label.hide()
        self.result_frame.show()
        self.previous_btn.show()
        self.st_index = 1
        self.one_cikarilan_items = list() 
        self.one_cikarilan_names = list()

        self.infos_text = '\n\n'.join([self.villa_dicts[i]["villa-info"] for i in range(len(self.villa_dicts))])
        self.textBrowser.setText(self.infos_text)

        # Sonucu gösteren bir bildirim mesajı göster
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Arama Sonuçları")
        msg_box.setText("Villa arama başarıyla tamamlandı!")
        msg_box.setInformativeText(f"{len(result)} tane uygun villa bulundu.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
        # QCompleter oluştur
        self.villa_names = list()
        for villa_dict in self.villa_dicts:
            self.villa_names.append(villa_dict["villa-name"])

        self.completer = QCompleter(self.villa_names, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.search_box.setCompleter(self.completer)
        
        # QCompleter'daki öğeye tıklanınca öğeyi seçilen villalar listesine ekle
        self.completer.activated.connect(self.add_selected_villa)
        self.selected_villas.model().rowsMoved.connect(self.update_text)
        
    def copy_infos(self):
        pyperclip.copy(self.infos_text)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('')
        msg_box.setText("Mesajlar kopyalandı!")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def rib_cb_changed(self):
    # Ranges in range check box - changed
        if not self.ranges_in_range_cb.checkState():
            self.holiday_range_frame.show()
            self.ranges_in_range_frame.hide()
        else:
            self.ranges_in_range_frame.show()
            self.holiday_range_frame.hide()

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
            self.villa_names.append(item.text())
            
            self.completer = QCompleter(self.villa_names, self)
            self.completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.completer.setFilterMode(Qt.MatchContains)
            self.search_box.setCompleter(self.completer)
            
            # QCompleter'daki öğeye tıklanınca öğeyi seçilen villalar listesine ekle
            self.completer.activated.connect(self.add_selected_villa)
            self.selected_villas.model().rowsMoved.connect(self.update_text)
            
            self.one_cikarilan_items.remove(item)
            self.one_cikarilan_names.remove(item.text())
            self.selected_villas.takeItem(self.selected_villas.row(item))
        self.update_text()

    def change_state(self, items, stateTo):
        for item in items:
            item.setCheckState(stateTo)
        self.last_clicked_item.setSelected(False)
        self.last_clicked_item = QListWidgetItem()
    
    def add_selected_villa(self, text):
        item = QListWidgetItem(text)
        self.one_cikarilan_items.append(item)
        self.one_cikarilan_names.append(item.text())
        self.villa_names.remove(item.text())
        self.selected_villas.addItem(item)

        # Completer'ı kaldır
        self.search_box.setCompleter(None)
        
        # Arama kutusunu temizle
        self.search_box.clear()

        self.completer = QCompleter(self.villa_names, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.search_box.setCompleter(self.completer)
        
        # QCompleter'daki öğeye tıklanınca öğeyi seçilen villalar listesine ekle
        self.completer.activated.connect(self.add_selected_villa)
        
        self.update_text()

    def update_text(self):
        put_forward_infos = "\n\n".join([self.villas[item.text()] for item in self.one_cikarilan_items])
        if put_forward_infos == "\n\n":
            put_forward_infos = ""
            
        normal_infos = []
        for villa_name in self.villa_names:
            normal_infos.append(self.villas[villa_name])
            
        normal_infos = "\n\n".join([self.villas[villa_name] for villa_name in self.villa_names])
        self.infos_text = put_forward_infos + "\n\n" + normal_infos
        self.textBrowser.setText(self.infos_text)

    def set_window_settings(self):
        self.setWindowTitle("Project Alpha | EKLENTI PAKETI")
        self.setWindowIcon(QIcon(os.path.join(BASE_DIR, 'static', 'img', 'window_icon.png')))
        self.show()
        
app = QApplication(sys.argv)
window = MainWindow()
sys.exit(app.exec_())