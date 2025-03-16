import pandas as pd
import json
import sqlalchemy as sa
from datetime import timedelta, datetime

class DailyStatusAnalyzer:
    def __init__(self):
        with open("config.json") as config_file:
            config = json.load(config_file)
        engine = sa.create_engine(config.get("sqlalchemy_uri"))
        df = pd.read_sql_query("""
            SELECT
                ts,
                activity,
                CASE WHEN activity = 'Boob'
                THEN quantity * 45
                ELSE quantity
                END AS quantity,
                NULLIF(duration, 0) AS duration
            FROM baby_log
            WHERE DATE(ts) = DATE(NOW())
            ORDER BY ts
            ;""", con=engine)
        self.df = df.sort_values("ts")

    def get_total(self, activities, metric):
        total = self.df.loc[self.df["activity"].isin(activities), metric].sum()
        total = f"{total:.0f}"
        return total
    
    def next_time(self, activity, hours):
        df = self.df[self.df["activity"] == activity]
        if not df.empty:
            latest = df.iloc[-1]["ts"]
            next_time = latest + timedelta(hours=hours)
            next_time = datetime.strftime(next_time, "%H:%M")
        else:
            next_time = None
        return next_time

    def last_feed_info(self):
        df = self.df[self.df["activity"].isin(["Boob", "Pumped", "Formula"])]
        if not df.empty:
            data = df.iloc[-1][["ts", "quantity"]].values.tolist()
            last_feed_info = "Time: %s | Qty: %s" % (datetime.strftime(data[0], "%H:%M"), str(data[1]))
        else:
            last_feed_info = None
        return last_feed_info
    
    def gather_data(self):
        daily_summary_data = {
            "next_nap": self.next_time("Nap", 1.5),
            "next_tongue_exercise":  self.next_time("Tongue Exercise", 4),
            "last_feed_info": self.last_feed_info(),
            "total_nap_time": self.get_total(["Nap"], "duration"),
            "food_consumed": self.get_total(["Boob", "Pumped", "Formula"], "quantity"),
            "food_consumption_goal": "720",
            "vit_d": self.get_total(["Vitamin D"], "quantity"),
            "antacid":  self.get_total(["Antacid"], "quantity")
        }
        return daily_summary_data

def main():
    dsa = DailyStatusAnalyzer()
    data = dsa.gather_data()
    print(data)


if __name__ == '__main__':
    main()