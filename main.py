import datetime
import sys
import time
import tkinter as tk
import uuid
import multiprocessing
from PIL import Image, ImageTk
import random
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import io
import os
import userpaths
import json

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def load_settings():
    global drinks_df
    global settings_dict
    global phrases_df

    if not os.path.isdir(save_path):
        os.makedirs(save_path)
    if os.path.exists(os.path.join(save_path, 'drinks.csv')):
        drinks_df = pd.read_csv(os.path.join(save_path, 'drinks.csv'), index_col=None,
                                dtype=drinks_schema)
    else:
        drinks_df.to_csv(path_or_buf=os.path.join(save_path, 'drinks.csv'), index=False)

    if os.path.exists(os.path.join(save_path, 'settings.json')):
        with open(os.path.join(save_path, 'settings.json'), 'r') as f:
            settings_dict = json.load(f)
    else:
        with open(os.path.join(save_path, 'settings.json'), 'w') as f:
            json.dump(settings_dict, f)

    if os.path.exists(os.path.join(save_path, 'phrases.csv')):
        phrases_df = pd.read_csv(os.path.join(save_path, 'phrases.csv'), index_col=None, dtype=phrases_schema)
    else:
        phrases_df.to_csv(path_or_buf=os.path.join(save_path, 'phrases.csv'), index=False)


    if not os.path.isdir(report_path):
        os.makedirs(report_path)



save_path = os.path.join(userpaths.get_my_documents(), 'Spruthusets-Børsbrandert')
report_path = os.path.join(userpaths.get_my_documents(), 'Spruthusets-Børsbrandert\Reports')

settings_dict = {
    "update_frequency": 5,
    "working_mode": 1,
    "scrolling_text_interval": 30,
    "graph_update_delay": 1
}

# Load CSV data into a pandas DataFrame
drinks_schema = {"ID": str, "Name": str, "Min. L. Price": float, "Min. U. Price": float, "Max. L. Price": float,
                 "Max. U. Price": float, "Starting Price": float,
                 "Short Name": str, "Group": int, "Price Decay": float, "Main Change": float, "Group Change": float,
                 "Reset Interval": float}
drinks_df = pd.DataFrame(columns=drinks_schema.keys()).astype(drinks_schema)

phrases_schema = {"Phrase": str}
phrases_df = pd.DataFrame(columns=phrases_schema.keys()).astype(phrases_schema)

load_settings()

# Sample dictionary mapping drink names to lists [minimum price, maximum price, starting price, current price]
drink_prices = {row['ID']: [row['Starting Price']] * 20 for _, row in drinks_df.iterrows()}
purchases = {row['ID']: 0 for _, row in drinks_df.iterrows()}
all_time_purchases = {row['ID']: [] for _, row in drinks_df.iterrows()}
price_vars = {}
price_vars_str = {}
current_min_reset = {row['ID']: random.uniform(row["Min. L. Price"], row["Min. U. Price"]) for _, row in
                     drinks_df.iterrows()}
current_max_reset = {row['ID']: random.uniform(row["Max. L. Price"], row["Max. U. Price"]) for _, row in
                     drinks_df.iterrows()}
canvas = None
root = None
timer_id = None
graph_queue_out = multiprocessing.Queue()
graph_queue_in = multiprocessing.Queue()
graph_images = {}
current_price_adjustment_count = 0
matplotlib.use('agg')
start_time = datetime.datetime.now()

def generate_today_so_far():
    drink_stats = []
    for index, drink_row in drinks_df.iterrows():
        drink_id = drink_row["ID"]
        drink_prices = all_time_purchases.get(drink_id, [])
        total_sales = len(drink_prices)
        if total_sales > 0:
            average_sale_price = sum(drink_prices) / total_sales
            starting_price = drink_row["Starting Price"]
            total_revenue = sum(drink_prices)
            total_discount = total_revenue - (total_sales * starting_price)
            total_discount_percentage = (((total_sales * starting_price) - total_revenue) / (total_sales * starting_price) * 100) * (-1)
        else:
            average_sale_price = 0
            starting_price = drink_row["Starting Price"]
            total_revenue = 0
            total_discount_percentage = 0
            total_discount = 0

        drink_stats.append({
            "Navn": drink_row["Name"],
            "Total Salg": total_sales,
            "Genms. Salgspris": round(average_sale_price, 2),
            "Total Omsætning": round(total_revenue, 2),
            "Startspris": starting_price,
            "Total Rabat": round(total_discount, 2),
            "Total Rabat %": round(total_discount_percentage, 2)
        })

    drink_prices = []
    for val in all_time_purchases.values():
        drink_prices.extend(val)
    total_sales = sum([len(x) for x in all_time_purchases.values()])
    if total_sales > 0:
        average_sale_price = sum(drink_prices) / total_sales
        total_revenue = sum(drink_prices)
    else:
        average_sale_price = 0
        total_revenue = 0

    total_discount = sum([x["Total Salg"] * x["Genms. Salgspris"] - x["Total Salg"] * x["Startspris"]  for x in drink_stats])
    original_price = sum([x["Total Salg"] * x["Startspris"] for x in drink_stats])
    if original_price == 0:
        total_discount_percentage = 0
    else:
        total_discount_percentage = (total_discount / original_price) * 100

    drink_stats.append({
        "Navn": "Total",
        "Total Salg": total_sales,
        "Genms. Salgspris": round(average_sale_price, 2),
        "Total Omsætning": round(total_revenue, 2),
        "Startspris": 0,
        "Total Rabat": round(total_discount, 2),
        "Total Rabat %": round(total_discount_percentage, 2)
    })

    # Create a DataFrame to hold the summary statistics for each drink
    drink_stats_df = pd.DataFrame(drink_stats)

    # Format the current date and time to include hour and minute
    file_name = start_time.strftime("%Y-%m-%d-%H-%M") + "_" + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M") + "_drink_stats.xlsx"

    # Join the report path and file name
    full_file_path = report_path + "\\" + file_name
    with pd.ExcelWriter(full_file_path) as writer:
        drink_stats_df.to_excel(writer, sheet_name="Overview")


def generate_year_so_far():
    today = datetime.datetime.now()
    read_schema = {"Navn": str, "Total Salg": float, "Genms. Salgspris": float, "Total Omsætning": float,
                   "Startspris": float, "Total Rabat %": float, "Total Rabat": float}

    daily_frames = {}
    for file_name in os.listdir(report_path):
        if "drink_stats" in file_name:
            s_time_str, e_time_str, suffix = file_name.split('_', 2)
            suffix = suffix.lower()  # Normalize the suffix to lower case

            # Try to parse the date and time parts
            start_dt = datetime.datetime.strptime(s_time_str, "%Y-%m-%d-%H-%M")
            end_dt = datetime.datetime.strptime(e_time_str, "%Y-%m-%d-%H-%M")

            # Check if the suffix is '_drink_stats.xlsx'
            if suffix == 'drink_stats.xlsx' and start_dt.year == today.year:
                file_path = os.path.join(report_path, file_name)

                with open(file_path, 'rb') as f:
                    df = pd.read_excel(f, engine='openpyxl', index_col=0, dtype=read_schema)
                    value = daily_frames.get(start_dt)
                    if value is None:
                        daily_frames[start_dt] = (end_dt, df)
                    elif value[0] < end_dt:
                        daily_frames[start_dt] = (end_dt, df)

    bingbong = {}
    for value in daily_frames.values():
        _, daily_frame = value
        for _, row in daily_frame.iterrows():
            if row["Navn"] != "Total":
                key = (row["Navn"], row["Startspris"])
                entry = bingbong.get(key)
                if entry is None:
                    bingbong[key] = (row["Total Salg"], row["Total Omsætning"])
                else:
                    bingbong[key] = (entry[0]+row["Total Salg"], entry[1]+row["Total Omsætning"])

    yearly = []
    for key, value in bingbong.items():
        name = key[0]
        total_sale = value[0]
        if total_sale == 0:
            average_sale_price = 0
        else:
            average_sale_price = value[1]/value[0]
        total_revenue = total_sale*average_sale_price
        starting_price = key[1]

        total_discount = total_sale*starting_price - total_sale*average_sale_price
        original_price = total_sale * starting_price
        if total_sale == 0:
            total_discount_percentage = 0
        else:
            total_discount_percentage = (total_discount / original_price) * 100 * (-1)

        yearly.append(
            {
                "Navn": name,
                "Total Salg": total_sale,
                "Genms. Salgspris": round(average_sale_price, 2),
                "Total Omsætning": round(total_revenue, 2),
                "Startspris": starting_price,
                "Total Rabat": round(total_discount, 2),
                "Total Rabat %": round(total_discount_percentage, 2)
            }
        )

    total_sale = sum([x["Total Salg"] for x in yearly])
    if total_sale == 0:
        average_sale_price = 0
    else:
        average_sale_price = sum([x["Total Omsætning"] for x in yearly]) / total_sale
    total_revenue = sum([x["Total Omsætning"] for x in yearly])

    total_discount = sum(x["Genms. Salgspris"]*x["Total Salg"] - x["Startspris"]*x["Total Salg"] for x in yearly)
    original_price = sum([x["Total Salg"] * x["Startspris"] for x in yearly])
    if total_sale == 0:
        total_discount_percentage = 0
    else:
        total_discount_percentage = (total_discount / original_price)*100

    total_entry = {
                "Navn": "Total",
                "Total Salg": total_sale,
                "Genms. Salgspris": round(average_sale_price, 2),
                "Total Omsætning": round(total_revenue, 2),
                "Startspris": 0,
                "Total Rabat": round(total_discount, 2),
                "Total Rabat %": round(total_discount_percentage, 2)
            }

    yearly.append(total_entry)

    yearly_df = pd.DataFrame(yearly)

    # Format the current date and time to include hour and minute
    file_name = start_time.strftime("%Y") + "_year-to-date.xlsx"

    # Join the report path and file name
    full_file_path = report_path + "\\" + file_name
    with pd.ExcelWriter(full_file_path) as writer:
        yearly_df.to_excel(writer, sheet_name="Overview")

def display_settings_window():
    # Function to display settings window
    working_mode_map = {"Efter Salg": 1, "Efter Tid": 2, "Efter Tid og Salg": 3}

    def save_settings():
        # Function to save settings when the save button is clicked
        global settings_dict
        global canvas

        # Map the selected option string to its corresponding integer value
        selected_option = working_mode_var.get()
        selected_mode = working_mode_map[selected_option]
        set_timer = settings_dict["working_mode"] == 1 and selected_mode > 1
        settings_dict["working_mode"] = selected_mode

        # Convert the update frequency to an integer
        settings_dict["update_frequency"] = int(update_frequency_var.get())

        # Convert the update frequency to an integer
        settings_dict["scrolling_text_interval"] = int(scrolling_text_interval_var.get())

        # Convert the update frequency to an integer
        settings_dict["graph_update_delay"] = int(graph_update_delay_var.get())

        if set_timer:
            update_price_image(True)

        # Save settings to settings.json file
        with open(os.path.join(save_path, 'settings.json'), 'w') as f:
            json.dump(settings_dict, f)

        # Close the settings window after saving
        settings_window.destroy()

    # Create window
    settings_window = tk.Toplevel()
    settings_window.title("Settings")

    # Labels and input fields for settings
    working_mode_label = tk.Label(settings_window, text="Opdater Drinkpriser:", font=('Arial', 14, 'bold'))
    working_mode_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

    # Map the selected option string to its corresponding integer value
    working_mode_map_reverse = {v: k for k, v in working_mode_map.items()}
    initial_mode = working_mode_map_reverse[settings_dict["working_mode"]]
    working_mode_var = tk.StringVar(value=initial_mode)

    max_option_width = max(len(option) for option in working_mode_map.keys())
    working_mode_selector = tk.OptionMenu(settings_window, working_mode_var, *working_mode_map.keys())
    working_mode_selector.config(font=('Arial', 14), width=max_option_width)  # Set width to accommodate longest option
    working_mode_selector.grid(row=0, column=1, padx=8, pady=5, sticky="e")

    update_frequency_label = tk.Label(settings_window, text="Opdaterings interval:", font=('Arial', 14, 'bold'))
    update_frequency_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    update_frequency_var = tk.StringVar(value=settings_dict["update_frequency"])
    update_frequency_entry = tk.Entry(settings_window, textvariable=update_frequency_var, font=('Arial', 14))
    update_frequency_entry.grid(row=1, column=1, padx=10, pady=5, sticky="e")

    scrolling_text_interval_label = tk.Label(settings_window, text="Nyheds interval:", font=('Arial', 14, 'bold'))
    scrolling_text_interval_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
    scrolling_text_interval_var = tk.IntVar(value=settings_dict["scrolling_text_interval"])
    scrolling_text_interval_entry = tk.Entry(settings_window, textvariable=scrolling_text_interval_var,
                                             font=('Arial', 14))
    scrolling_text_interval_entry.grid(row=2, column=1, padx=10, pady=5, sticky="e")

    graph_update_delay_label = tk.Label(settings_window, text="Graf opdateringstid:", font=('Arial', 14, 'bold'))
    graph_update_delay_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
    graph_update_delay_var = tk.IntVar(value=settings_dict["graph_update_delay"])
    graph_update_delay_entry = tk.Entry(settings_window, textvariable=graph_update_delay_var,
                                        font=('Arial', 14))
    graph_update_delay_entry.grid(row=3, column=1, padx=10, pady=5, sticky="e")

    # Save button
    save_button = tk.Button(settings_window, text="Gem", font=('Arial', 14, 'bold'), command=save_settings)
    save_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

    # Configure column widths to be the same
    settings_window.grid_columnconfigure(0, weight=1)
    settings_window.grid_columnconfigure(1, weight=1)


def display_phrases_table():
    global phrases_df

    def add_phrase_row():
        # Add a new row for a phrase
        new_index = len(entries)
        entry_var = tk.StringVar()
        entry = tk.Entry(table_frame, textvariable=entry_var, font=('Arial', 14), width=50)  # Adjust width here
        entry.grid(row=new_index + 1, column=0, padx=5, pady=0)
        entries.append(entry_var)
        entry_widgets.append(entry)  # Append the Entry widget to the list
        delete_buttons.append(
            tk.Button(table_frame, text="-", font=('Arial', 12), command=lambda i=new_index: delete_phrase_row(i)))
        delete_buttons[new_index].grid(row=new_index + 1, column=1, padx=5, pady=0)

    def delete_phrase_row(index):
        # Delete a row for a phrase
        entries.pop(index)  # Remove the entry variable at the specified index
        entry_widgets[index].grid_forget()
        delete_buttons[index].grid_forget()

    def save_phrases():
        global phrases_df

        # Create a list to store new entries
        new_entries = []

        # Add new entries to the list
        for entry in entries:
            new_entries.append({'Phrase': entry.get()})

        # Create a new DataFrame from the list of dictionaries
        new_phrases_df = pd.DataFrame(new_entries)

        # Save the new DataFrame to CSV
        new_phrases_df.to_csv(path_or_buf=os.path.join(save_path, 'phrases.csv'), index=False)

        # Update phrases_df with the new DataFrame
        phrases_df = new_phrases_df

        # Perform subsequent code
        if os.path.exists(os.path.join(save_path, 'phrases.csv')):
            phrases_df = pd.read_csv(os.path.join(save_path, 'phrases.csv'), index_col=None, dtype=phrases_schema)
        else:
            phrases_df.to_csv(path_or_buf=os.path.join(save_path, 'phrases.csv'), index=False)
        table_window.destroy()

    # Create a new window
    table_window = tk.Toplevel()
    table_window.title("Phrases Table")
    table_window.geometry("800x600")

    # Create a frame inside the window to hold the table and scrollbar
    frame = tk.Frame(table_window)
    frame.pack(fill="both", expand=True)

    # Create a canvas
    canvas = tk.Canvas(frame)
    canvas.pack(side="left", fill="both", expand=True)

    # Add a scrollbar
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    # Configure the canvas
    canvas.configure(yscrollcommand=scrollbar.set)

    # Bind scrollbar to the canvas
    scrollbar.config(command=canvas.yview)

    # Create another frame inside the canvas to hold the table
    table_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=table_frame, anchor="nw")

    # Bind canvas scrolling to the scrollbar
    table_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # Get phrases from DataFrame
    phrases = phrases_df["Phrase"].tolist()

    # Create labels for column headers
    label = tk.Label(table_frame, text="Nyheder", font=('Arial', 14, 'bold'))
    label.grid(row=0, column=0)

    # Create entry variables for phrases
    # Create entry widgets for phrases
    entries = []
    entry_widgets = []  # Store entry widgets here
    delete_buttons = []
    for i, phrase in enumerate(phrases):
        entry_var = tk.StringVar(value=phrase)
        entry = tk.Entry(table_frame, textvariable=entry_var, font=('Arial', 14), width=50)  # Adjust width here
        entry.grid(row=i + 1, column=0, padx=5, pady=0)
        entries.append(entry_var)
        entry_widgets.append(entry)  # Store entry widgets
        delete_button = tk.Button(table_frame, text="-", font=('Arial', 12),
                                  command=lambda index=i: delete_phrase_row(index))
        delete_button.grid(row=i + 1, column=1, padx=5, pady=0, sticky="nsew")
        delete_buttons.append(delete_button)

    # Add button to add a new phrase
    new_phrase_button = tk.Button(table_window, text="Ny Linje", font=('Arial', 14, 'bold'), command=add_phrase_row)
    new_phrase_button.pack(pady=10)

    # Add button to save phrases
    save_button = tk.Button(table_window, text="Gem", font=('Arial', 14, 'bold'), command=save_phrases)
    save_button.pack(pady=10)


def display_drink_table():
    global drinks_df
    global drinks_schema

    column_widths = [15, 12, 12, 12, 12, 12, 12, 5, 12, 12, 12, 12,
                     12]  # Define widths for each column (excluding the first column)

    def add_drink_row():
        # Add a new row for a phrase
        new_index = len(entries)
        entry_var_list = []
        entry_var_list.append(uuid.uuid4())
        for col_index, header in enumerate(headers, start=1):  # Exclude the first column
            entry_var = tk.StringVar()
            width = column_widths[col_index - 1]  # Get width from the list based on column index
            entry = tk.Entry(table_frame, textvariable=entry_var, font=('Arial', 14), width=width)
            entry.grid(row=new_index + 1, column=col_index, padx=5, pady=0)
            entry_var_list.append(entry_var)
            entry_widgets.append(entry)  # Append the Entry widget to the list
        entries.append(entry_var_list)

        delete_button = tk.Button(table_frame, text="-", font=('Arial', 12),
                                  command=lambda i=new_index: delete_drink_row(i))
        delete_button.grid(row=new_index + 1, column=len(headers) + 1, padx=5, pady=0, sticky="nsew")
        delete_buttons.append(delete_button)

    def delete_drink_row(index):
        # Delete a row for a phrase
        entries.pop(index)
        for entry_widget in entry_widgets[index]:
            entry_widget.grid_forget()
        delete_buttons[index].grid_forget()

    def save_drinks():
        def show_validation_error(column_name, drink_name):
            top = tk.Toplevel(table_window)
            top.geometry("600x50")
            top.title("Valideringsfejl")
            error_message = f"Valideringsfejl for  '{drink_name}'. Værdien '{column_name}' er ikke korrekt."
            label = tk.Label(top, text=error_message, font=('Arial', 14, 'bold'))
            label.pack()

        global drinks_df
        global root

        # Create a list to store new entries
        new_entries = []

        # Add new entries to the list and perform type casting and validation
        for entry_list in entries:
            new_entry = {}
            new_entry["ID"] = entry_list[0]
            for col_index, (header, entry_var) in enumerate(zip(headers, entry_list[1:]), start=1):
                value = entry_var.get()
                try:
                    # Perform type casting based on the schema
                    if drinks_schema[header] == str:
                        new_entry[header] = str(value)
                    elif drinks_schema[header] == int:
                        new_entry[header] = int(value)
                    elif drinks_schema[header] == float:
                        new_entry[header] = float(value)
                    else:
                        new_entry[header] = value
                except ValueError:
                    # Validation failed, show error message
                    show_validation_error(header, new_entry["Name"])
                    return
            new_entries.append(new_entry)

        # Create a new DataFrame from the list of dictionaries
        new_drinks_df = pd.DataFrame(new_entries)

        # Save the new DataFrame to CSV
        new_drinks_df.to_csv(path_or_buf=os.path.join(save_path, 'drinks.csv'), index=False)

        # Update drinks_df with the new DataFrame
        drinks_df = new_drinks_df

        # Destroy the table window
        root.destroy()

    # Create a new window
    table_window = tk.Toplevel()
    table_window.title("Drink Table")
    table_window.geometry("1920x1080")

    # Create a frame inside the window to hold the table and scrollbar
    frame = tk.Frame(table_window)
    frame.pack(fill="both", expand=True)

    # Create a canvas
    canvas = tk.Canvas(frame)
    canvas.pack(side="left", fill="both", expand=True)

    # Add a scrollbar
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    # Configure the canvas
    canvas.configure(yscrollcommand=scrollbar.set)

    # Create another frame inside the canvas to hold the table
    table_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=table_frame, anchor="nw")

    # Bind canvas scrolling to the scrollbar
    table_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # Get column names from DataFrame excluding the first column (ID)
    headers = list(drinks_schema.keys())[1:]

    # Create labels for column headers
    for col_index, header in enumerate(headers):
        label = tk.Label(table_frame, text=header, font=('Arial', 14, 'bold'))
        label.grid(row=0, column=col_index + 1, padx=5, pady=0)

    # Create a list to hold the drinks data
    entries = []
    entry_widgets = [[] for _ in range(len(drinks_df))]
    delete_buttons = []

    # Add existing drinks data
    for i, row in drinks_df.iterrows():
        entry_var_list = []
        entry_var_list.append(str(uuid.uuid4()))
        for col_index, header in enumerate(headers, start=1):  # Exclude the first column
            entry_var = tk.StringVar(value=row[header])
            width = column_widths[col_index - 1]  # Get width from the list based on column index
            entry = tk.Entry(table_frame, textvariable=entry_var, font=('Arial', 14), width=width)
            entry.grid(row=i + 1, column=col_index, padx=5, pady=0)
            entry_var_list.append(entry_var)
            entry_widgets[i].append(entry)  # Store entry widgets
        entries.append(entry_var_list)
        delete_button = tk.Button(table_frame, text="-", font=('Arial', 12),
                                  command=lambda index=i: delete_drink_row(index))
        delete_button.grid(row=i + 1, column=len(headers) + 1, padx=5, pady=0, sticky="nsew")
        delete_buttons.append(delete_button)

    # Add button to add a new drink
    new_drink_button = tk.Button(table_window, text="Ny Linje", font=('Arial', 14, 'bold'), command=add_drink_row)
    new_drink_button.pack(pady=10)

    # Add button to save drinks
    save_button = tk.Button(table_window, text="Gem", font=('Arial', 14, 'bold'), command=save_drinks)
    save_button.pack(pady=10)


def display_data(window):
    # Function to display data in a new window

    def add_count(drink_id):
        # Function to add count when add button is clicked
        count_vars[drink_id].set(count_vars[drink_id].get() + 1)
        update_total()

    def subtract_count(drink_id):
        # Function to subtract count when subtract button is clicked
        current_count = count_vars[drink_id].get()
        if current_count > 0:
            count_vars[drink_id].set(current_count - 1)
            update_total()

    def update_total():
        total = sum(count_vars[drink_id].get() * drink_prices.get(drink_id, [])[-1] for drink_id in count_vars)
        footer_total.config(text="{:.2f}".format(total))

    def reset_counts():
        for drink_id in count_vars:
            all_time_purchases[drink_id].extend([drink_prices.get(drink_id, 0)[-1]]*(count_vars[drink_id].get()))
            purchases[drink_id] += count_vars[drink_id].get()
            count_vars[drink_id].set(0)
        update_total()

    def end_day():
        generate_today_so_far()
        generate_year_so_far()

    def save_and_update_image():
        # Save counts and update the image if working_mode is 1 or 3
        reset_counts()
        if settings_dict["working_mode"] in [1, 3]:
            update_price_image(False)

    # Create window
    window.title("Product Information")

    # Set window size to 1920x1080
    window.geometry("1920x1080")

    # Table frame
    table_frame = tk.Frame(window)
    table_frame.pack(fill="both", expand=True)


    # Set fixed width for the name column
    col_widths = [170, 80, 80, 130, 40, 40, 40]

    #Table frames padding
    table_frame_padding = 20

    # Create left, middle, and right frames
    header_frame = tk.Frame(table_frame)
    header_frame.pack()

    header_left_frame = tk.Frame(header_frame)
    header_left_frame.grid_configure(row=0, column=0, padx=table_frame_padding)

    header_middle_frame = tk.Frame(header_frame)
    header_middle_frame.grid_configure(row=0, column=1, padx=table_frame_padding)

    header_right_frame = tk.Frame(header_frame)
    header_right_frame.grid_configure(row=0, column=2, padx=table_frame_padding)


    for frame in [header_left_frame, header_middle_frame, header_right_frame]:
        # Create labels for each column
        labels = ['Navn', 'Min.', 'Max.', 'Nu', '', '', '' '']
        frame.grid_rowconfigure(0, minsize=100)
        for i, label in enumerate(labels):
            # Align text to the left for 'Navn' and to the right for other labels
            anchor = "w" if label == 'Navn' else "e"
            label_widget = tk.Label(frame, text=label, font=('Arial', 22, 'bold'), anchor=anchor)
            label_widget.grid(row=0, column=i, sticky="nsew")
            frame.grid_columnconfigure(i, minsize=col_widths[i])

    # Display data in three columns
    count_vars = {}
    total = 0  # Variable to store the total cost
    entries_frame = tk.Frame(table_frame)
    entries_frame.pack()

    entries_y_min_size = 50

    # Group drinks by 'Group' column
    for group in drinks_df['Group'].unique():
        group_frame = tk.Frame(entries_frame)
        group_frame.pack()

        left_frame = tk.Frame(group_frame)
        left_frame.grid_configure(row=0, column=0, padx=table_frame_padding)
        middle_frame = tk.Frame(group_frame)
        middle_frame.grid_configure(row=0, column=1, padx=table_frame_padding)
        right_frame = tk.Frame(group_frame)
        right_frame.grid_configure(row=0, column=2, padx=table_frame_padding)

        grouped_drinks = drinks_df.loc[drinks_df['Group'] == group]
        sorted_grouped_drinks = grouped_drinks.sort_values(by='Name')
        sorted_grouped_drinks = sorted_grouped_drinks.reset_index(drop=True)

        for index, row in sorted_grouped_drinks.iterrows():
            id = row['ID']
            name = row['Name']
            minimum_price = int(row['Min. L. Price'])  # Convert to integer
            maximum_price = int(row['Max. U. Price'])  # Convert to integer

            # Fetch current price from the dictionary
            current_price_var_str = price_vars_str[id]
            current_price_var = price_vars[id]

            # Display the values alternately in left, middle, and right frames
            values = [name, minimum_price, maximum_price, current_price_var_str]
            frame_to_use = left_frame if index % 3 == 0 else middle_frame if index % 3 == 1 else right_frame
            for i, value in enumerate(values):
                # Align text to the left for 'Navn' and to the right for other values
                anchor = "w" if i == 0 else "e"
                if i != 3:
                    value_label = tk.Label(frame_to_use, text=f"{value}", font=('Arial', 18), anchor=anchor)
                else:
                    value_label = tk.Label(frame_to_use, textvariable=value, font=('Arial', 18), anchor=anchor)
                value_label.grid(row=index // 3 + 1, column=i, sticky="nsew")
                frame_to_use.grid_columnconfigure(i, minsize=col_widths[i])

            # Add buttons for adding and subtracting counts
            count_var = tk.IntVar(value=0)  # Create IntVar for count
            count_vars[id] = count_var  # Add count variable to the dictionary
            add_button = tk.Button(frame_to_use, text="+", font=('Arial', 14), command=lambda x=id: add_count(x))
            add_button.grid(row=index // 3 + 1, column=4, padx=5, pady=5, sticky="nsew")
            frame_to_use.grid_columnconfigure(4, minsize=col_widths[4])

            subtract_button = tk.Button(frame_to_use, text="-", font=('Arial', 14),
                                        command=lambda x=id: subtract_count(x))
            subtract_button.grid(row=index // 3 + 1, column=5, padx=5, pady=5, sticky="nsew")
            frame_to_use.grid_columnconfigure(5, minsize=col_widths[5])

            # Add count column starting at 0
            count_label = tk.Label(frame_to_use, textvariable=count_var, font=('Arial', 18), anchor="e", width=2)
            count_label.grid(row=index // 3 + 1, column=6, padx=5, pady=5, sticky="nsew")
            frame_to_use.grid_columnconfigure(6, minsize=col_widths[6])

            # Calculate total cost and update the total variable
            total += count_var.get() * current_price_var.get()

            # Adjust row height
            frame_to_use.grid_rowconfigure(index // 3 + 1, minsize=entries_y_min_size)

        filler_entries = 0 if 3- len(sorted_grouped_drinks.index) % 3 == 3 else 3 - len(sorted_grouped_drinks.index) % 3
        filler_frames = [right_frame, middle_frame]
        for i in range(filler_entries):
            frame_to_use = filler_frames[i]
            row = len(sorted_grouped_drinks.index) // 3 + 1
            for k in range(7):
                label = tk.Label(frame_to_use, text=f"", font=('Arial', 18), anchor="w")
                label.grid(row=row, column=k)
                frame_to_use.grid_columnconfigure(k, minsize=col_widths[k])

            frame_to_use.grid_rowconfigure(row, minsize=entries_y_min_size)

        for frame in [left_frame, middle_frame, right_frame]:
            row = len(sorted_grouped_drinks.index) // 3 + 2
            frame.grid_rowconfigure(row, minsize=15)
            for k in range(7):
                label = tk.Label(frame, text=f"")
                label.grid(row=row, column=k)

    footer_frame = tk.Frame(window)

    # Add a button to open the drink table window
    drink_table_button = tk.Button(footer_frame, text="Drinks", font=('Arial', 16), command=display_drink_table,
                                   width=10)
    drink_table_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    # Create button to display settings window
    settings_button = tk.Button(footer_frame, text="Settings", font=('Arial', 16), command=display_settings_window,
                                width=10)
    settings_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

    # Add button to open phrases
    phrases_button = tk.Button(footer_frame, text="Nyheder", font=('Arial', 16), command=display_phrases_table,
                               width=10)
    phrases_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

    # Add button to end day
    end_day_button = tk.Button(footer_frame, text="Rapport", font=('Arial', 16), command=end_day, width=10)
    end_day_button.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    filler_columns = 15
    for i in range(filler_columns):
        total_label_1 = tk.Label(footer_frame, text="", width=10)
        total_label_2 = tk.Label(footer_frame, text="", width=10)
        total_label_1.grid(row=0, column=2+i)
        total_label_2.grid(row=1, column=2+i)


    # Add footer label for "Total:"
    total_label = tk.Label(footer_frame, text="Total:", font=('Arial', 20, 'bold'))
    total_label.grid(row=0, column=2+filler_columns, padx=(10, 10), pady=10, sticky="ew")

    # Add footer for total cost
    footer_total = tk.Label(footer_frame, text=str(total), font=('Arial', 20, 'bold'))
    footer_total.grid(row=0, column=3+filler_columns, padx=(0, 50), pady=10, sticky="ew")

    # Add button to reset counts
    sell_button = tk.Button(footer_frame, text="Sælg", font=('Arial', 16), command=save_and_update_image, width=10)
    sell_button.grid(row=1, column=2+filler_columns, padx=10, pady=10, sticky="ew")

    # Add button to reset counts
    reset_button = tk.Button(footer_frame, text="Reset", font=('Arial', 16), command=reset_counts, width=10)
    reset_button.grid(row=1, column=3+filler_columns, padx=10, pady=10, sticky="ew")


    # Place the footer frame at the bottom of the window
    footer_frame.place(relx=0.5, rely=0.9, anchor=tk.CENTER)


def create_text_with_outline(canvas, x, y, text, font=("Helvetica", 12), fill="white", outline="black", thickness=2,
                             anchor="center", angle=0, tag="base"):
    # Create the outline by drawing slightly shifted text in all 8 directions
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if abs(dx) + abs(dy) != 0:  # Skip the center text
                canvas.create_text(x + dx, y + dy, text=text, font=font, fill=outline, anchor=anchor, angle=angle,
                                   tag=tag)

    # Create the main text
    canvas.create_text(x, y, text=text, font=font, fill=fill, anchor=anchor, angle=angle, tag=tag)


def adjust_prices():
    global current_price_adjustment_count
    global purchases
    global current_min_reset
    global current_max_reset
    current_price_adjustment_count += 1
    updated_prices = {}

    # Find the most sold item and its group
    if len(purchases) > 0:
        most_sold_item_id = max(purchases, key=purchases.get)
        most_sold_group = drinks_df.loc[drinks_df['ID'] == most_sold_item_id, 'Group'].iloc[0]

    for drink_id, prices in drink_prices.items():
        latest_price = prices[-1]  # Get the latest price

        # Get drink information
        # Ensure new price stays within range
        name = drinks_df.loc[drinks_df['ID'] == drink_id, 'Name'].iloc[0]
        minimum_price = current_min_reset[drink_id]
        maximum_price = current_max_reset[drink_id]
        start_price = drinks_df.loc[drinks_df['ID'] == drink_id, 'Starting Price'].iloc[0]
        reset_interval = drinks_df.loc[drinks_df['ID'] == drink_id, 'Reset Interval'].iloc[0]

        # Define random ranges for changes
        main_change_range = drinks_df.loc[drinks_df['ID'] == drink_id, 'Main Change'].iloc[0]
        group_change_range = drinks_df.loc[drinks_df['ID'] == drink_id, 'Group Change'].iloc[0]
        price_decay_range = drinks_df.loc[drinks_df['ID'] == drink_id, 'Price Decay'].iloc[0]

        # Apply random changes within the specified ranges
        main_change = random.uniform(0, main_change_range)
        group_change = random.uniform(0, group_change_range)
        price_decay = random.uniform(0, price_decay_range)

        # Increase price for most sold item and its group
        if len(purchases) > 0 and drink_id == most_sold_item_id:
            new_price = latest_price + main_change * start_price
        elif len(purchases) > 0 and drinks_df.loc[drinks_df['ID'] == drink_id, 'Group'].iloc[0] == most_sold_group:
            new_price = latest_price + group_change * start_price
        else:
            # Decrease price based on price decay
            new_price = latest_price - price_decay * start_price

        # Check if price exceeds reset percentage above maximum or below minimum
        if new_price < current_min_reset[drink_id] or current_max_reset[drink_id] < new_price:
            min_l_price = drinks_df.loc[drinks_df['ID'] == drink_id, 'Min. L. Price'].iloc[0]
            min_u_price = drinks_df.loc[drinks_df['ID'] == drink_id, 'Min. U. Price'].iloc[0]
            max_l_price = drinks_df.loc[drinks_df['ID'] == drink_id, 'Max. L. Price'].iloc[0]
            max_u_price = drinks_df.loc[drinks_df['ID'] == drink_id, 'Max. U. Price'].iloc[0]

            current_min_reset[drink_id] = random.uniform(min_l_price, min_u_price)
            current_max_reset[drink_id] = random.uniform(max_l_price, max_u_price)

            new_price = start_price + random.uniform(-reset_interval, reset_interval) * start_price

        new_price = max(minimum_price, min(new_price, maximum_price))
        new_price = round(new_price, 2)

        # Update tkinter variable with new price
        price_vars[drink_id].set(new_price)
        price_vars_str[drink_id].set("{:.2f}".format(new_price))

        # Append new price to list and remove oldest if exceeds limit
        prices.append(new_price)
        if len(prices) > 20:
            prices.pop(0)

        updated_prices[drink_id] = new_price

    purchases = {row['ID']: 0 for _, row in drinks_df.iterrows()}
    return updated_prices


def get_graph_image_process(queue_in, queue_out):
    while True:
        try:
            q_res = queue_in.get()
        except:
            q_res = None
        if q_res is not None:
            queued_price_adjustment_count, drink_id, graph_x, graph_y, graph_width, graph_height, minimum_price, maximum_price, drink_prices, start_price = q_res
            # Create a fig
            fig, ax = plt.subplots(figsize=(graph_width // 5, graph_height // 5))

            # Plot price history on the existing figure
            last_5_prices = drink_prices[drink_id][-5:]
            xs = range(len(last_5_prices))
            ys = last_5_prices
            ax.plot(xs, [start_price]*len(last_5_prices), marker='', linewidth=35, linestyle='dashed', dashes=(3, 2), color='black')
            ax.plot(xs, ys, marker='', linewidth=130, color='black')
            ax.plot(xs, ys, marker='', linewidth=70, color='white')
            ax.set_ylim(minimum_price - 3, maximum_price + 3)
            ax.axis('off')
            plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
            plt.tight_layout()

            # Save the figure as a PNG image
            buf = io.BytesIO()
            fig.savefig(buf, format='png', transparent=True)
            buf.seek(0)
            plt.close(fig)

            graph_image = Image.open(buf)
            resized_graph_image = graph_image.resize((graph_width, graph_height), Image.Resampling.LANCZOS)
            queue_out.put((queued_price_adjustment_count, drink_id, graph_x, graph_y, graph_width, graph_height,
                           resized_graph_image))


def get_price_image():
    width = 1920
    height = 1080
    prices = adjust_prices()

    global timer_id
    global current_price_adjustment_count
    if timer_id is not None:
        canvas.after_cancel(timer_id)

    timer_id = canvas.after(100, lambda i=current_price_adjustment_count: consume_from_queue(i, 0))

    # Clear existing content on canvas
    canvas.delete("all")

    # Load and display the background image
    bg_image = Image.open(resource_path("bg.jpg"))
    bg_photo = ImageTk.PhotoImage(bg_image)
    bg_image.close()

    canvas.create_image(0, 0, image=bg_photo, anchor='nw')
    create_text_with_outline(canvas, width // 2, height // 15, anchor="center",
                             text="Børsbrandert", font=("Josefin Sans", 50), fill='white')

    # Define padding
    left_padding = 100
    right_padding = 100
    column_padding = 75  # Padding between columns

    # Calculate column width
    num_columns = 3
    column_width = (width - left_padding - right_padding - (num_columns - 1) * column_padding) // num_columns

    # Define base positions
    column_bases = [left_padding + i * (column_width + column_padding) for i in range(num_columns)]
    row_base = 200
    row_height = 80

    for idx, (drink_id, price) in enumerate(prices.items()):
        # Determine column and row index
        column_idx = idx % num_columns
        row_idx = idx // num_columns

        # Calculate position for current item
        column_base = column_bases[column_idx]
        row_position = row_base + row_idx * row_height

        name = drinks_df.loc[drinks_df['ID'] == drink_id, 'Name'].iloc[0]
        short_name = drinks_df.loc[drinks_df['ID'] == drink_id, 'Short Name'].iloc[0]
        current_price = prices[drink_id]
        start_price = drinks_df.loc[drinks_df['ID'] == drink_id, 'Starting Price'].iloc[0]
        maximum_price = drinks_df.loc[drinks_df['ID'] == drink_id, 'Max. U. Price'].iloc[0]
        minimum_price = drinks_df.loc[drinks_df['ID'] == drink_id, 'Min. L. Price'].iloc[0]

        # Get the previous price from the list of prices
        previous_price = drink_prices[drink_id][-2] if len(drink_prices[drink_id]) >= 2 else drink_prices[drink_id][-1]

        # Determine if the price has gone up, down, or remained unchanged
        discount = int((1-(current_price/start_price))*100)

        # Set the fill color based on the discount
        fill_color = "green" if discount > 0 else "red" if discount < 0 else "white"
        #{'-' if int(start_price-current_price) < 0 else '+' if int(start_price-current_price) > 0 else ''}

        drink_price = prices[drink_id]
        # Extract the whole number part and the decimal part
        whole_number_part = int(drink_price)
        decimal_part = drink_price - whole_number_part

        # Format the decimal part to always have two decimal points
        decimal_part_formatted = "{:.2f}".format(decimal_part)[2:]

        create_text_with_outline(canvas, column_base, row_position, anchor="w",
                                 text=f"{name}", font=("Josefin Sans", 26), fill='white')
        create_text_with_outline(canvas, column_base + 225, row_position + 20,
                                 anchor="w", text=f"{short_name}", font=("Josefin Sans", 12), fill='white',
                                 angle=90)
        create_text_with_outline(canvas, column_base + 335, row_position - 5,
                                 anchor="n", text=f"{abs(discount)}%", font=("Josefin Sans", 20), fill=fill_color, angle=90)

        create_text_with_outline(canvas, column_base + 500, row_position - 12,
                                 anchor="e", text=f"{whole_number_part}.", font=("Josefin Sans", 50), fill='white')
        create_text_with_outline(canvas, column_base + 545, row_position + 5,
                                 anchor="e", text=f"{decimal_part_formatted}", font=("Josefin Sans", 25),
                                 fill='white')

        create_text_with_outline(canvas, column_base + 545, row_position - 20,
                                 anchor="e", text=f"DKK", font=("Josefin Sans", 16), fill='white')

        canvas.image = bg_photo
        # Graph size
        graph_width = 100
        graph_height = 40
        graph_x = column_base + 240
        graph_y = row_position - 25


        # Overlay the grey box underneath the graph image
        canvas.create_rectangle(graph_x - 2, graph_y - 2, graph_x + graph_width + 4, graph_y + graph_height + 4,
                                fill='gray50', outline='black', width=2, stipple='gray25')

        # Overlay the grey box underneath the graph image
        canvas.create_rectangle(0, 980, 1920, 1080, fill='gray50', outline='black', width=2, stipple='gray25')

        graph_queue_in.put((current_price_adjustment_count, drink_id, graph_x, graph_y, graph_width, graph_height,
                            minimum_price, maximum_price, drink_prices, start_price))


def consume_from_queue(price_adjustment_count, processed_images_amount):
    global graph_queue_out
    global canvas
    try:
        q_res = graph_queue_out.get_nowait()
    except:
        q_res = None

    processed_images = processed_images_amount

    if q_res is not None:
        queued_price_adjustment_count, drink_id, graph_x, graph_y, graph_width, graph_height, resized_graph_image = q_res
        if queued_price_adjustment_count == price_adjustment_count:
            # Convert the resized image to a Tkinter PhotoImage object
            graph_photo = ImageTk.PhotoImage(resized_graph_image)
            graph_images[drink_id] = graph_photo
            canvas.create_image(graph_x, graph_y, image=graph_photo, anchor='nw')
            processed_images += 1
        elif queued_price_adjustment_count > price_adjustment_count:
            graph_queue_out.put((queued_price_adjustment_count, drink_id, graph_x, graph_y, graph_width, graph_height,
                                 resized_graph_image))

    if processed_images_amount < len(drinks_df.index):
        canvas.after(100, lambda i=current_price_adjustment_count: consume_from_queue(price_adjustment_count,
                                                                                      processed_images))


def update_price_image(queue_timer):
    get_price_image()
    if queue_timer and settings_dict["working_mode"] > 1:
        canvas.after(settings_dict["update_frequency"] * 1000, update_price_image, True)


def scroll_text(text, x):
    canvas.delete("SCROLLING_TEXT")
    if x > -1000:
        create_text_with_outline(canvas, x, 1010, anchor="w", text=f"{text}", font=("Josefin Sans", 40), fill='white',
                                 tag="SCROLLING_TEXT")
        canvas.after(25, scroll_text, text, x - 3)


def init_scrolling_text():
    global phrases_df

    # Select a random row from the DataFrame
    if len(phrases_df.index) > 0:
        random_row = random.choice(phrases_df.index)
        random_phrase = phrases_df.loc[random_row, "Phrase"]  # Adjusted column name

        scroll_text(random_phrase, 2000)

        canvas.after(settings_dict["scrolling_text_interval"] * 1000, init_scrolling_text)


def display_background_image(window):
    global canvas
    global current_price_adjustment_count
    # Set window title and geometry
    window.title("Prisoversigt")
    window.geometry("1920x1080")

    # Create canvas
    canvas = tk.Canvas(window, width=1920, height=1080, bg='white')
    canvas.pack()

    # Schedule the update of the background image
    update_price_image(True)  # Start timer at beginning of program
    canvas.after(10, init_scrolling_text)

    window.mainloop()


def main():
    global root
    # Start graph computation process
    graph_process = multiprocessing.Process(target=get_graph_image_process, args=[graph_queue_in, graph_queue_out])
    graph_process.start()

    # Create main Tkinter window
    root = tk.Tk()
    root.title("Main Window")
    root.geometry("1920x1080")
    for index, row in drinks_df.iterrows():
        id = str(row['ID'])  # Convert name to string
        price_vars.update({id: tk.IntVar(value=int(row['Starting Price']))})  # Convert to integer
        price_vars_str.update({id: tk.StringVar(value="{:.2f}".format(row['Starting Price']))})
    # Call display_data() to create data display window
    display_data(root)

    # Call display_background_image() to create background image window
    display_background_image(tk.Toplevel(root))

    # Start the main event loop
    root.mainloop()

    graph_process.terminate()
    graph_process.join()  # Wait for the process to terminate before exiting


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        # On Windows calling this function is necessary.
        multiprocessing.freeze_support()
    main()
