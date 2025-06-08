import pandas as pd
import json
import sqlalchemy as sa
from datetime import timedelta, datetime

class DailyStatusAnalyzer:
    """Class for handling daily status data retrieval and display."""
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
        """Gets the sum for the given activities, per metric.
        
        Args:
            activities (list): the list of activites we want to sum up.
            metric (string): the metric we want to sum.
            
        Returns:
            total (string): the sum, formatted to zero decimal places.
        """
        total = self.df.loc[self.df["activity"].isin(activities), metric].sum()
        total = f"{total:.0f}"
        return total
    
    def next_time(self, activity, hours=0):
        """The next time an activity should occur. This can also be used to calculate the last time something occurred, if you don't supply the 'hours' argument.
        
        Args:
            activity (string): the activity that we want to calculate the next time for.
            hours (int): the number of hours we want to add to the last time something occured.
            
        Returns:
            next_time (string): the next time the activity should occur.
        """
        df = self.df[self.df["activity"] == activity]
        if not df.empty:
            latest = df.iloc[-1]["ts"]
            next_time = latest + timedelta(hours=hours)
            next_time = datetime.strftime(next_time, "%H:%M")
        else:
            next_time = None
        return next_time

    def last_feed_info(self):
        """
        Fetch the information regarding the last feed.
        
        Returns:
            last_feed_info (string): a string that contains the time and quantity of the last feed.
        """
        df = self.df[self.df["activity"].isin(["Boob", "Pumped", "Formula"])]
        if not df.empty:
            data = df.iloc[-1][["ts", "quantity"]].values.tolist()
            last_feed_info = "Time: %s | Qty: %s" % (datetime.strftime(data[0], "%H:%M"), str(data[1]))
        else:
            last_feed_info = None
        return last_feed_info
    
    def gather_data(self):
        """
        Collects the data to pass on to the template.
        
        Returns:
            daily_summary_data (dict): the data that will end up in the template.
        """
        daily_summary_data = {
            "next_nap": self.next_time("Nap", 2.5),
            "last_paracetemol":  self.next_time("Paracetemol", 0),
            "last_feed_info": self.last_feed_info(),
            "total_nap_time": self.get_total(["Nap"], "duration"),
            "food_consumed": self.get_total(["Boob", "Pumped", "Formula"], "quantity"),
            "food_consumption_goal": "720",
            "vit_d": self.get_total(["Vitamin D"], "quantity"),
            "antacid":  self.get_total(["Antacid"], "quantity"),
            "antibiotic":  self.get_total(["Antibiotic"], "quantity")
        }
        return daily_summary_data

def main():
    dsa = DailyStatusAnalyzer()
    data = dsa.gather_data()
    print(data)


if __name__ == '__main__':
    main()