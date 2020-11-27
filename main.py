import requests  # для запросов
import json
import pandas as pd  # для анализа данных
from pandastable import Table  # для создания таблиц
from bokeh.plotting import figure
from bokeh.models import HoverTool, LabelSet, ColumnDataSource
from bokeh.tile_providers import get_provider, CARTODBPOSITRON  # для оформления карты
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler  # обработчик, принимающий функцию Python

from tkinter import *  # для создания форм приложения
from tkinter import messagebox
from tkinter.ttk import Combobox

import webbrowser  # для автоматического открытия браузера
from datetime import datetime  # для перевода в Unix time и создания запроса об аэропорте

import numpy as np  # для подсчета большого кол-ва координат самолетов
import math

window = Tk()
window.title("Flight Radar")
window.geometry("350x200")
window.resizable(width=False, height=False)
color = "grey"
window.configure(background=color)

continent_label = Label(window, text="Выберите континент", background=color, foreground="white")
continent_label.pack()
combo = Combobox(window,  width=20)
combo["values"] = ("Мир", "Европа", "Азия", "Африка", "Северная Америка", "Южная Америка", "Австралия")
combo.current(0)  # вариант по умолчанию
combo.pack()


def to_mercator(lon, lat):
    num = lon * 0.017453292519943295
    x = 6378137.0 * num
    a = lat * 0.017453292519943295
    x_mercator = x
    y_mercator = 3189068.5 * math.log((1.0 + math.sin(a)) / (1.0 - math.sin(a)))
    return x_mercator, y_mercator


def plane_to_mercator(df, lon="long", lat="lat"):
    num = df[lon] * 0.017453292519943295
    df["x"] = 6378137.0 * num
    a = df[lat] * 0.017453292519943295
    df["y"] = 3189068.5 * np.log((1.0 + np.sin(a)) / (1.0 - np.sin(a)))
    return df


# отслеживание полета самолетов
def flightradar(flight):

    # Координаты
    lomin, lamin, lomax, lamax = 0, 0, 0, 0
    name = combo.get()  # присваивание переменной значения из combobox

    if name == "Мир":
        lomin = -153.984
        lamin = -58.814
        lomax = 178.593
        lamax = 83.195

    elif name == "Европа":
        lomin = -9.4042
        lamin = 36.1023
        lomax = 69.257
        lamax = 76.921

    elif name == "Азия":
        lomin = 63.281
        lamin = -1.757
        lomax = 182.812
        lamax = 81.201

    elif name == "Африка":
        lomin = -18.281
        lamin = -34.742
        lomax = 50.273
        lamax = 34.179

    elif name == "Северная Америка":
        lomin = -159.961
        lamin = 10.833
        lomax = -10.547
        lamax = 84.089

    elif name == "Южная Америка":
        lomin = -91.934
        lamin = -58.263
        lomax = -34.453
        lamax = 16.299

    elif name == "Австралия":
        lomin = 109.687
        lamin = -48.225
        lomax = 180.351
        lamax = -12.897

    # запрос api
    username = "MVXZ"
    password = "pythonproject"
    opensky_url = "https://" + username + ":" + password + "@opensky-network.org/api/states/all?" + "lamin=" + \
                  str(lamin) + "&lomin=" + str(lomin) + "&lamax=" + str(lamax) + "&lomax=" + str(lomax)

    # преобразование координат
    xy_min = to_mercator(lomin, lamin)
    xy_max = to_mercator(lomax, lamax)

    # координатный диапазон в веб-проекции Меркатора
    x_range = ([xy_min[0], xy_max[0]])
    y_range = ([xy_min[1], xy_max[1]])

    flightradar_source = ColumnDataSource({
        "icao24": [], "callsign": [], "origin_country": [], "time_position": [], "last_contact": [], "long": [],
        "lat": [], "baro_altitude": [], "on_ground": [], "velocity": [], "true_track": [], "vertical_rate": [],
        "sensors": [], "geo_altitude": [], "squawk": [], "spi": [], "position_source": [], "x": [], "y": [],
        "rotation": [], "url": []
    })

    # построение карты
    world = figure(x_range=x_range, y_range=y_range, x_axis_type="mercator", y_axis_type="mercator",
                   sizing_mode="scale_width", plot_height=300, tools="pan,wheel_zoom,save,reset")
    world_style = get_provider("CARTODBPOSITRON")
    world.add_tile(world_style, level="image")
    world.image_url(url="url", x="x", y="y", source=flightradar_source, anchor="center", angle_units="deg",
                    angle="rotation", h_units="screen", w_units="screen", w=40, h=40)
    world.circle("x", "y", source=flightradar_source, fill_color="black", hover_color="red", size=10,
                 fill_alpha=0.8, line_width=0)

    world_hover = HoverTool()  # отображение данных при наведении на самолет

    world_hover.tooltips = [
        ("Номер рейса", "@callsign"),
        ("Страна отправления", "@origin_country"),
        ("Скорость (м/с)", "@velocity"),
        ("Высота (м)", "@baro_altitude"),
        ("Широта", "@lat"),
        ("Долгота", "@long")
    ]

    world_labels = LabelSet(x="x", y="y", text="callsign", level="glyph", x_offset=5, y_offset=5,
                            source=flightradar_source, render_mode="canvas", background_fill_color="white",
                            text_font_size="8pt")

    world.add_tools(world_hover)
    world.add_layout(world_labels)
    world.title.text = "Flight Radar"

    flight.title = "FLIGHT RADAR"
    flight.add_root(world)

    # обновление данных
    def update():
        information = requests.get(opensky_url).json()

        # загрузка данных в Pandas
        titles = ["icao24",
                  "callsign",
                  "origin_country",
                  "time_position",
                  "last_contact",
                  "long",
                  "lat",
                  "baro_altitude",
                  "on_ground",
                  "velocity",
                  "true_track",
                  "vertical_rate",
                  "sensors",
                  "geo_altitude",
                  "squawk",
                  "spi",
                  "position_source"]
        plane_data = information["states"]
        plane_df = pd.DataFrame(plane_data, columns=titles)
        plane_to_mercator(plane_df)
        plane_df.fillna("Нет данных", inplace=True)  # замена пустых значений на "Нет данных"
        plane_df["rotation"] = plane_df["true_track"] * -1  # угол поворота
        icon_url = "https://cdn4.iconfinder.com/data/icons/ionicons/512/icon-plane-512.png"  # картинка самолета
        plane_df["url"] = icon_url
        roll = len(plane_df.index)
        plane_df = plane_df.to_dict(orient="list")  # конвертация в словарь
        flightradar_source.stream(plane_df, roll)

    # обновление данных в заданный интервал
    flight.add_periodic_callback(update, 5000)  # 5с.для зарегистрированных пользователей,10с.не для зарегистрированных


def airports():
    window.withdraw()
    airports_window = Toplevel(window)
    airports_window.title("Airports")
    airports_window.geometry("350x250")
    airports_window.resizable(width=False, height=False)
    airports_window.configure(background=color)
    x_airpwindow = (airports_window.winfo_screenwidth() - airports_window.winfo_reqwidth()) / 2
    y_airpwindow = (airports_window.winfo_screenheight() - airports_window.winfo_reqheight()) / 2
    airports_window.wm_geometry("+%d+%d" % (x_airpwindow, y_airpwindow))

    code_label = Label(airports_window, text="Введите код ICAO аэропорта", background=color, foreground="white")
    code_label.pack()
    code = Entry(airports_window, width=16)
    code.pack()

    period_label = Label(airports_window, text="За какой период вывести данные (кол-во дней)", background=color,
                         foreground="white")
    period_label.pack()
    period_combo = Combobox(airports_window, width=15)
    period_combo["values"] = (1, 2, 3, 4, 5, 6, 7)
    period_combo.current(0)
    period_combo.pack()

    def arrival():
        today = datetime.now()  # получение текущей даты
        today = datetime.timestamp(today)  # перевод даты в Unix time
        today = round(today)  # округление
        period = today - 86400*int(period_combo.get())  # вычитание времени в секундах до предыдущей даты

        airport_code = code.get()
        airport_code.upper()

        username = "MVXZ"
        password = "pythonproject"
        url_airports = "https://" + username + ":" + password + "@opensky-network.org/api/flights/arrival?" + \
                       "airport=" + str(airport_code) + "&begin=" + str(period) + "&end=" + str(today)
        information = requests.get(url_airports).json()
        airport_df = pd.DataFrame(information)

        arrival_window = Toplevel(window)
        arrival_window.title("Прибытия")
        arrival_window.resizable(width=False, height=False)
        arrival_window.configure(background=color)
        x_arrwindow = (arrival_window.winfo_screenwidth() - arrival_window.winfo_reqwidth()) / 2
        y_arrwindow = (arrival_window.winfo_screenheight() - arrival_window.winfo_reqheight()) / 2
        arrival_window.wm_geometry("+%d+%d" % (x_arrwindow, y_arrwindow))

        frame = Frame(arrival_window)
        frame.pack(fill="both", expand=True)
        table_arr = Table(frame, dataframe=airport_df)
        table_arr.show()

        def close_window():
            arrival_window.destroy()

        close_button = Button(arrival_window, text="Закрыть окно", highlightbackground=color, command=close_window)
        close_button.pack()

    def departure():
        today = datetime.now()  # получение текущей даты
        today = datetime.timestamp(today)  # перевод даты в Unix time
        today = round(today)  # округление
        period = today - 86400*int(period_combo.get())  # вычитание времени в секундах до предыдущей даты

        airport_code = code.get()
        airport_code.upper()

        username = "MVXZ"
        password = "pythonproject"
        url_airports = "https://" + username + ":" + password + "@opensky-network.org/api/flights/departure?" + \
                       "airport=" + str(airport_code) + "&begin=" + str(period) + "&end=" + str(today)
        information = requests.get(url_airports).json()
        airport_df = pd.DataFrame(information)

        departure_window = Toplevel(window)
        departure_window.title("Отправления")
        departure_window.resizable(width=False, height=False)
        departure_window.configure(background=color)
        x_depwindow = (departure_window.winfo_screenwidth() - departure_window.winfo_reqwidth()) / 2
        y_depwindow = (departure_window.winfo_screenheight() - departure_window.winfo_reqheight()) / 2
        departure_window.wm_geometry("+%d+%d" % (x_depwindow, y_depwindow))

        frame = Frame(departure_window)
        frame.pack(fill="both", expand=True)
        table_arr = Table(frame, dataframe=airport_df)
        table_arr.show()

        def close_window():
            departure_window.destroy()

        close_button = Button(departure_window, text="Закрыть окно", highlightbackground=color, command=close_window)
        close_button.pack()

    def back():
        airports_window.destroy()
        window.deiconify()

    arrival_button = Button(airports_window, text="Вывести прибытия", highlightbackground=color, foreground="#7e1cff",
                            width=20, height=1, command=arrival)
    arrival_button.pack()

    departure_button = Button(airports_window, text="Вывести отправления", highlightbackground=color,
                              foreground="#7e1cff", width=20, height=1, command=departure)
    departure_button.pack()

    back_button = Button(airports_window, text="назад", highlightbackground=color, foreground="#414141", width=7,
                         height=1, command=back)
    back_button.pack()


def excel_doc():
    lon_min = -153.984
    lat_min = -58.814
    lon_max = 178.593
    lat_max = 83.195
    username = "MVXZ"
    password = "pythonproject"
    url_data = "https://" + username + ":" + password + '@opensky-network.org/api/states/all?' + 'lamin=' + \
               str(lat_min) + "&lomin=" + str(lon_min) + "&lamax=" + str(lat_max) + "&lomax=" + str(lon_max)
    information = requests.get(url_data).json()

    col_name = ["icao24", "callsign", "origin_country", "time_position", "last_contact", "long", "lat",
                "baro_altitude", "on_ground", "velocity", "true_track", "vertical_rate", "sensors", "geo_altitude",
                "squawk", "spi", "position_source"]
    flight_df = pd.DataFrame(information["states"], columns=col_name)
    flight_df.fillna("Нет данных", inplace=True)
    flight_df.to_excel("flight_data.xlsx")


# запуск сервера
def start_server():
    if combo.get() != "":
        messagebox.showinfo("Info", "Сервер успешно запущен!")
        app = Application(FunctionHandler(flightradar))
        server = Server(app, port=8084)
        webbrowser.get(using="safari").open_new_tab("localhost:8084")  # открытие браузера
        server.run_until_shutdown()
    else:
        messagebox.showerror("Ошибка", "Заполните данные")


# закрытие программы
def close_app():
    res = messagebox.askquestion("Выход", "Вы действительно хотите закрыть программу?")
    if res == "yes":
        window.destroy()
    else:
        messagebox.showinfo("Возвращение", "Открытие программы")


def about_flightradar():
    messagebox.showinfo("Информация", "Flight Radar\n2020\nПроект по питону")


def help_w():
    help_window = Toplevel(window)
    help_window.title("Help")
    help_window.geometry("500x150")
    help_window.resizable(width=False, height=False)
    help_window.configure(background=color)
    x_helpwindow = (help_window.winfo_screenwidth() - help_window.winfo_reqwidth()) / 2
    y_helpwindow = (help_window.winfo_screenheight() - help_window.winfo_reqheight()) / 2
    help_window.wm_geometry("+%d+%d" % (x_helpwindow, y_helpwindow))

    info_help_w = Label(help_window, text="Инструкция", background=color, foreground="white")
    info_help_w.pack()

    instruction = "1. Выберите континент из выпадающего списка;\n" \
                  "2. Нажмите кнопку 'Запустить сервер';\n" \
                  "3. В новой вкладке браузера откроется окно с заданными настройками;\n" \
                  "4. Для просмотра информации об авиарейсе наведите курсор на самолет."
    instr = Label(help_window, text=instruction, justify=LEFT, background=color, foreground="white")
    instr.pack()

    def close_window():
        help_window.destroy()

    close_button = Button(help_window, text="Закрыть окно",  highlightbackground=color, command=close_window)
    close_button.pack()
    help_window.mainloop()


def airports_icao():
    icao_window = Toplevel(window)
    icao_window.title("ICAO")
    icao_window.geometry("350x350")
    icao_window.resizable(width=False, height=False)
    icao_window.configure(background=color)
    x_icaowindow = (icao_window.winfo_screenwidth() - icao_window.winfo_reqwidth()) / 2
    y_icaowindow = (icao_window.winfo_screenheight() - icao_window.winfo_reqheight()) / 2
    icao_window.wm_geometry("+%d+%d" % (x_icaowindow, y_icaowindow))

    icao_df = pd.DataFrame({
        "Аэропорт": ["Домодедово", "Шереметьево", "Внуково", "Пулково", "El Prat", "Flughafen Wien", ],
        "Код ICAO": ["UUDD", "UUEE", "UUWW", "ULLI", "LEBL", "LOWW", ],
        "Город": ["Москва", "Москва", "Москва", "Санкт-Петербург", "Barcelona", "Wien", ],
    })

    frame = Frame(icao_window)
    frame.pack(fill="both", expand=True)

    table_icao = Table(frame, dataframe=icao_df)
    table_icao.show()

    def close_window():
        icao_window.destroy()

    close_button = Button(icao_window, text="Закрыть окно",  highlightbackground=color, command=close_window)
    close_button.pack()
    icao_window.mainloop()


# кнопка запуска сервера
btn_start = Button(window, text="Запустить программу", highlightbackground=color, foreground="purple", width=20,
                   height=1, command=start_server)
btn_start.pack()


airports_button = Button(window, text="Аэропорты", highlightbackground=color,  foreground="blue", width=20, height=1,
                         command=airports)
airports_button.pack()


# кнопка сохранения данных в excel
excel_button = Button(window, text="Excel", highlightbackground=color,  foreground="green", width=20, height=1,
                      command=excel_doc)
excel_button.pack()


mainmenu = Menu(window)
window.config(menu=mainmenu)

filemenu = Menu(mainmenu, tearoff=0)
filemenu.add_command(label="О приложении Flight Radar", command=about_flightradar)
filemenu.add_separator()
filemenu.add_command(label="Выход", command=close_app)

helpmenu = Menu(mainmenu, tearoff=0)
helpmenu.add_command(label="Справка Flight Radar", command=help_w)
helpmenu.add_separator()
helpmenu.add_command(label="Коды ICAO аэропортов", command=airports_icao)

mainmenu.add_cascade(label="Flight Radar", menu=filemenu)
mainmenu.add_cascade(label="Справка", menu=helpmenu)

# вывод окна программы по центру экрана
x_window = (window.winfo_screenwidth() - window.winfo_reqwidth()) / 2
y_window = (window.winfo_screenheight() - window.winfo_reqheight()) / 2
window.wm_geometry("+%d+%d" % (x_window, y_window))

window.mainloop()
