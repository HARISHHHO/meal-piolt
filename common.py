"""
common.py - shared stuff for all the MealPilot agent assignments.

Keeps the dish table, recipes, prices and a tiny logger in one place so every
assignment uses the same data and the logs look the same.
"""
import os
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


class Logger:
    """
    Very small logger. Prints to console and (after open()) to logs/<name>.log.
    `redirect` is used by the capstone so every module writes into ONE log file.
    """
    redirect = None

    def __init__(self, name):
        self.name = name
        self.fh = None
        self.echo = True
        self.t0 = time.time()
        self.lock = threading.Lock()

    def open(self):
        self.fh = open(os.path.join(LOG_DIR, self.name + ".log"), "w", encoding="utf-8")
        self.t0 = time.time()
        return self

    def __call__(self, tag, msg):
        if Logger.redirect is not None and Logger.redirect is not self:
            Logger.redirect(tag, msg)
            return
        with self.lock:
            line = "+%7.3fs [%-8s] %s" % (time.time() - self.t0, tag, msg)
            if self.echo:
                print(line, flush=True)
            if self.fh:
                self.fh.write(line + "\n")
                self.fh.flush()

    def raw(self, text=""):
        """write a line without the timestamp (used for tables / banners)"""
        with self.lock:
            if self.echo:
                print(text, flush=True)
            if self.fh:
                self.fh.write(text + "\n")
                self.fh.flush()


# ---------------------------------------------------------------------------
# Dish table. cost = rupees per serving, prep = minutes, fibre/protein in grams
# ---------------------------------------------------------------------------
DISHES = {
    "dal_tadka":    dict(label="Dal Tadka + Jeera Rice",  kcal=520, protein=18, fibre=9,  cost=55,
                         prep=40, veg=True,  soft=True,  allergens=[]),
    "rajma_chawal": dict(label="Rajma Chawal",            kcal=610, protein=20, fibre=12, cost=65,
                         prep=60, veg=True,  soft=False, allergens=[]),
    "chole_roti":   dict(label="Chole + Roti",            kcal=640, protein=19, fibre=11, cost=60,
                         prep=50, veg=True,  soft=False, allergens=[]),
    "paneer_masala": dict(label="Paneer Masala + Roti",   kcal=720, protein=26, fibre=5,  cost=120,
                          prep=35, veg=True,  soft=False, allergens=["dairy"]),
    "veg_khichdi":  dict(label="Vegetable Khichdi",       kcal=430, protein=14, fibre=7,  cost=40,
                         prep=30, veg=True,  soft=True,  allergens=[]),
    "idli_sambar":  dict(label="Idli + Sambar",           kcal=380, protein=12, fibre=6,  cost=35,
                         prep=25, veg=True,  soft=True,  allergens=[]),
    "egg_curry":    dict(label="Egg Curry + Roti",        kcal=560, protein=24, fibre=5,  cost=70,
                         prep=30, veg=False, soft=False, allergens=["egg"]),
    "chicken_curry": dict(label="Chicken Curry + Rice",   kcal=650, protein=36, fibre=3,  cost=140,
                          prep=45, veg=False, soft=False, allergens=[]),
    "curd_rice":    dict(label="Curd Rice + Pickle",      kcal=350, protein=10, fibre=2,  cost=30,
                         prep=15, veg=True,  soft=True,  allergens=["dairy"]),
    "moong_chilla": dict(label="Moong Dal Chilla",        kcal=340, protein=17, fibre=6,  cost=35,
                         prep=20, veg=True,  soft=True,  allergens=[]),
    "palak_paneer": dict(label="Palak Paneer + Roti",     kcal=590, protein=24, fibre=7,  cost=110,
                         prep=35, veg=True,  soft=False, allergens=["dairy"]),
    "veg_upma":     dict(label="Vegetable Upma",          kcal=320, protein=8,  fibre=5,  cost=28,
                         prep=20, veg=True,  soft=True,  allergens=["nuts"]),
}

# kg (or litre) of each ingredient needed per person per serving
RECIPES = {
    "dal_tadka":     {"dal": .06, "rice": .08, "tomato": .05, "onion": .04},
    "rajma_chawal":  {"rajma": .07, "rice": .09, "tomato": .06, "onion": .05},
    "chole_roti":    {"chole": .07, "atta": .08, "tomato": .05, "onion": .05},
    "paneer_masala": {"paneer": .10, "atta": .08, "tomato": .08, "onion": .05},
    "veg_khichdi":   {"rice": .06, "dal": .04, "veg_mix": .08},
    "idli_sambar":   {"rice": .07, "dal": .05, "veg_mix": .06, "tomato": .02},
    "egg_curry":     {"egg": .12, "atta": .08, "tomato": .06, "onion": .06},
    "chicken_curry": {"chicken": .15, "rice": .09, "tomato": .06, "onion": .07},
    "curd_rice":     {"rice": .07, "curd": .12},
    "moong_chilla":  {"moong": .08, "onion": .03, "tomato": .03},
    "palak_paneer":  {"paneer": .08, "palak": .10, "atta": .08},
    "veg_upma":      {"sooji": .07, "veg_mix": .06, "onion": .03},
}

# market prices, rupees per kg
PRICES = {
    "rice": 55, "dal": 130, "atta": 45, "tomato": 40, "onion": 35, "paneer": 380,
    "egg": 110, "chicken": 230, "curd": 70, "rajma": 140, "chole": 120, "palak": 40,
    "moong": 120, "sooji": 55, "veg_mix": 60,
}


def shopping_list(menu, headcount):
    """menu = list of dish ids (one serving per person each). returns {item: kg}"""
    need = {}
    for dish in menu:
        for item, per_head in RECIPES[dish].items():
            need[item] = round(need.get(item, 0) + per_head * headcount, 3)
    return need


def price_of(need, prices=None):
    prices = prices or PRICES
    return round(sum(qty * prices[item] for item, qty in need.items()), 2)
