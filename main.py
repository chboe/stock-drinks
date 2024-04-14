import sys
import time
import tkinter as tk
from PIL import Image, ImageTk
import random
import pandas as pd
import matplotlib.pyplot as plt
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
    global df
    global settings_dict
    if not os.path.isdir(save_path):
        os.makedirs(save_path)
    if os.path.exists(os.path.join(save_path, 'drinks.csv')):
        df = pd.read_csv(os.path.join(save_path, 'drinks.csv'), index_col=None,
                         dtype=schema)
    else:
        df.to_csv(path_or_buf=os.path.join(save_path, 'drinks.csv'), index=False)

    if os.path.exists(os.path.join(save_path, 'settings.json')):
        with open(os.path.join(save_path, 'settings.json'), 'r') as f:
            settings_dict = json.load(f)
    else:
        with open(os.path.join(save_path, 'settings.json'), 'w') as f:
            json.dump(settings_dict, f)


save_path = os.path.join(userpaths.get_my_documents(), 'Spruthusets-Børsbrandert')
settings_dict = {
  "update_frequency": 5,
  "working_mode": 1
}

# Load CSV data into a pandas DataFrame
schema = {"ID": str, "Name": str, "Minimum Price": float, "Maximum Price": float, "Starting Price": float, "Short Name": str, "Group": int, "Total Sens.": float, "Group Sens.": float, "Rand. Sens.": float, "Price Scal. Fact.": float, "Trend Chg. Prob.": float}
df = pd.DataFrame(columns=schema.keys()).astype(schema)

load_settings()

# Sample dictionary mapping drink names to lists [minimum price, maximum price, starting price, current price]
drink_prices = {row['ID']: [row['Starting Price']] * 20 for _, row in df.iterrows()}
purchases = {row['ID']: 0 for _, row in df.iterrows()}
price_vars = {}
price_vars_str = {}
canvas = None
drinks_variables_dict = {}

graph_images = [None] * len(df.index)


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

        if set_timer:
            update_background_image(canvas)

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

    # Save button
    save_button = tk.Button(settings_window, text="Gem", font=('Arial', 14, 'bold'), command=save_settings)
    save_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    # Configure column widths to be the same
    settings_window.grid_columnconfigure(0, weight=1)
    settings_window.grid_columnconfigure(1, weight=1)

def display_drink_table():
    global drinks_variables_dict
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
    canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # Create another frame inside the canvas to hold the table
    table_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=table_frame, anchor="nw")

    # Get column names from DataFrame excluding "Current Price"
    headers = list(schema.keys())[1:]

    # Create labels for column headers
    for col_index, header in enumerate(headers):
        label = tk.Label(table_frame, text=header, font=('Arial', 14, 'bold'))
        label.grid(row=0, column=col_index)

    # Create input fields for each row and column in the DataFrame

    row_index = 1
    def add_row(row_index, series=None):
        new_row = [""] * len(headers)  # Create a new row with empty strings
        for col_index, value in enumerate(new_row):
            if headers[col_index] in ["Name", "Short Name"]:
                var = tk.StringVar()
            elif headers[col_index] in ["Group"]:
                var = tk.IntVar()
            else:
                var = tk.DoubleVar()

            if series is not None:
                var.set(series[headers[col_index]])

            entry = tk.Entry(table_frame, textvariable=var, font=('Arial', 14), width=15, borderwidth=1, relief="solid")
            entry.grid(row=row_index, column=col_index)  # Corrected the row index here
            # Store the variable in the dictionary by ID and header
            drinks_variables_dict[(row_index, headers[col_index])] = var
        # Add delete row button for the new row
        delete_button = tk.Button(table_frame, text="-", font=('Arial', 12), command=lambda idx=row_index: delete_row(idx))
        delete_button.grid(row=row_index, column=len(headers) + 1, padx=5, pady=0, sticky="nsew")
        # Update the canvas scrolling region after adding a new row
        table_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    add_row_button = tk.Button(table_window, text="Ny Drink", font=('Arial', 14, 'bold'), command=lambda idx=row_index: add_row(idx))
    add_row_button.pack(pady=10)
    for index, row in df.iterrows():
        add_row(row_index, row)
        row_index += 1

    # Update the canvas scrolling region
    table_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

    def delete_row(row_index):
        # Function to delete the specified row
        for col_name in headers:
            # Remove the variable from the dictionary by ID and header
            del drinks_variables_dict[(row_index, col_name)]
        table_frame.grid_slaves(row=row_index)[0].grid_forget()  # Forget the widgets in the specified row
        # Update the canvas scrolling region after deleting the row
        table_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def save_data():
        # Function to save the data from the table to the DataFrame
        global df
        df = pd.DataFrame(columns=headers)  # Create an empty DataFrame with columns
        for (row_index, col_name), var in drinks_variables_dict.items():
            value = var.get()  # Get the value from the entry widget
            df.at[row_index - 1, col_name] = value  # Update the DataFrame with the value
        # Save the DataFrame to CSV
        save_path = os.path.join(userpaths.get_my_documents(), 'Spruthusets-Børsbrandert')
        df.to_csv(os.path.join(save_path, 'drinks.csv'), index=False)

        # Refresh the display_data window
        table_window.destroy()  # Close the current window
        display_data()  # Reopen the display_data window

        # Call update_background_image(False)
        update_background_image(False)

    # Save button
    save_button = tk.Button(table_window, text="Gem", font=('Arial', 14, 'bold'), command=save_data)
    save_button.pack(pady=10)

    # Configure column widths to be the same
    table_window.grid_columnconfigure(0, weight=1)
    table_window.grid_columnconfigure(1, weight=1)

def display_data(window):
    # Function to display data in a new window

    def add_count(drink_name):
        # Function to add count when add button is clicked
        count_vars[drink_name].set(count_vars[drink_name].get() + 1)
        update_total()

    def subtract_count(drink_name):
        # Function to subtract count when subtract button is clicked
        current_count = count_vars[drink_name].get()
        if current_count > 0:
            count_vars[drink_name].set(current_count - 1)
            update_total()

    def update_total():
        total = sum(count_vars[drink_name].get() * drink_prices.get(drink_name, [])[-1] for drink_name in count_vars)
        footer_total.config(text="{:.2f}".format(total))

    def reset_counts():
        for drink_name in count_vars:
            purchases[drink_name] += count_vars[drink_name].get()
            count_vars[drink_name].set(0)
        update_total()

    def save_and_update_image():
        # Save counts and update the image if working_mode is 1 or 3
        reset_counts()
        if settings_dict["working_mode"] in [1, 3]:
            update_background_image(False)

    # Create window
    window.title("Product Information")

    # Set window size to 1920x1080
    window.geometry("1920x1080")

    # Header title
    header_label = tk.Label(window, text="Produktoversigt", font=('Arial', 24, 'bold'))
    header_label.pack(padx=10, pady=10)

    # Create parent frame to hold left, middle, and right frames
    parent_frame = tk.Frame(window)
    parent_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Create left, middle, and right frames
    left_frame = tk.Frame(parent_frame)
    left_frame.pack(side="left", fill="both", expand=True)
    middle_frame = tk.Frame(parent_frame)
    middle_frame.pack(side="left", fill="both", expand=True)
    right_frame = tk.Frame(parent_frame)
    right_frame.pack(side="left", fill="both", expand=True)

    # Set fixed width for the name column
    name_column_width = 200

    # Create labels for each column
    labels = ['Navn', 'Min.', 'Max.', 'Nu']
    for i, label in enumerate(labels):
        # Align text to the left for 'Navn' and to the right for other labels
        anchor = "w" if label == 'Navn' else "e"
        label_text = label if len(label) <= 10 else label[:7] + "..."
        label_widget_left = tk.Label(left_frame, text=label_text, font=('Arial', 22, 'bold'), anchor=anchor)
        label_widget_left.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

        label_widget_middle = tk.Label(middle_frame, text=label_text, font=('Arial', 22, 'bold'), anchor=anchor)
        label_widget_middle.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

        label_widget_right = tk.Label(right_frame, text=label_text, font=('Arial', 22, 'bold'), anchor=anchor)
        label_widget_right.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

        # Set fixed width for the name column
        if label == 'Navn':
            left_frame.grid_columnconfigure(i, minsize=name_column_width)
            middle_frame.grid_columnconfigure(i, minsize=name_column_width)
            right_frame.grid_columnconfigure(i, minsize=name_column_width)

    # Display data in three columns
    count_vars = {}
    total = 0  # Variable to store the total cost
    for index, row in df.iterrows():
        id = row['ID']
        name = row['Name']
        minimum_price = int(row['Minimum Price'])  # Convert to integer
        maximum_price = int(row['Maximum Price'])  # Convert to integer
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
            value_label.grid(row=index // 3 + 1, column=i, padx=10, pady=5, sticky="nsew")
            frame_to_use.grid_columnconfigure(i, weight=1)  # Make columns expandable

        # Add buttons for adding and subtracting counts
        count_var = tk.IntVar(value=0)  # Create IntVar for count
        count_vars[id] = count_var  # Add count variable to the dictionary
        add_button = tk.Button(frame_to_use, text="+", font=('Arial', 14), command=lambda x=id: add_count(x))
        add_button.grid(row=index // 3 + 1, column=5, padx=5, pady=5, sticky="nsew")

        subtract_button = tk.Button(frame_to_use, text="-", font=('Arial', 14),
                                    command=lambda x=id: subtract_count(x))
        subtract_button.grid(row=index // 3 + 1, column=6, padx=5, pady=5, sticky="nsew")

        # Add count column starting at 0
        count_label = tk.Label(frame_to_use, textvariable=count_var, font=('Arial', 18), anchor="e", width=2)
        count_label.grid(row=index // 3 + 1, column=7, padx=5, pady=5, sticky="nsew")

        # Calculate total cost and update the total variable
        total += count_var.get() * current_price_var.get()

        # Adjust row height
        frame_to_use.grid_rowconfigure(index // 3 + 1, minsize=30)  # Set minimum row height to 30 pixels

    footer_frame = tk.Frame(window)

    # Add footer label for "Total:"
    total_label = tk.Label(footer_frame, text="Total:", font=('Arial', 20, 'bold'))
    total_label.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")

    # Add footer for total cost
    footer_total = tk.Label(footer_frame, text=str(total), font=('Arial', 20, 'bold'))
    footer_total.grid(row=0, column=1, padx=(0, 50), pady=10, sticky="ew")

    # Add a button to open the drink table window
    drink_table_button = tk.Button(footer_frame, text="Drinks", font=('Arial', 16), command=display_drink_table,
                                   width=10)
    drink_table_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

    # Create button to display settings window
    settings_button = tk.Button(footer_frame, text="Settings", font=('Arial', 16), command=display_settings_window,
                                width=10)
    settings_button.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    # Add button to reset counts
    reset_button = tk.Button(footer_frame, text="Gem", font=('Arial', 16), command=save_and_update_image, width=10)
    reset_button.grid(row=1, column=2, padx=10, pady=10, sticky="ew")

    # Place the footer frame at the bottom of the window
    footer_frame.place(relx=0.5, rely=0.9, anchor=tk.CENTER)

def create_text_with_outline(canvas, x, y, text, font=("Helvetica", 12), fill="white", outline="black", thickness=2,
                             anchor="center", angle=0):

    # Create the outline by drawing slightly shifted text in all 8 directions
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if abs(dx) + abs(dy) != 0:  # Skip the center text
                canvas.create_text(x + dx, y + dy, text=text, font=font, fill=outline, anchor=anchor, angle=angle)

    # Create the main text
    canvas.create_text(x, y, text=text, font=font, fill=fill, anchor=anchor, angle=angle)

def adjust_prices():
    purchases = {row['ID']: 0 for _, row in df.iterrows()}
    updated_prices = {}
    total_purchases = sum(purchases.values())

    for drink_id, prices in drink_prices.items():
        num_purchases = purchases.get(drink_id, 0)
        latest_price = prices[-1]  # Get the latest price
        total_sensitivity = df.loc[df['ID'] == drink_id, 'Total Sens.'].iloc[0]
        random_sensitivity = df.loc[df['ID'] == drink_id, 'Rand. Sens.'].iloc[0]
        price_scaling_factor = df.loc[df['ID'] == drink_id, 'Price Scal. Fact.'].iloc[0]

        # Calculate price change based on total sales and Total Sens.
        if total_purchases > 0:
            total_sales_factor = num_purchases / total_purchases
            total_price_change = total_sales_factor * total_sensitivity
        else:
            total_price_change = 0

        # Find the group for the current drink
        group = df.loc[df['ID'] == drink_id, 'Group'].iloc[0]

        # Calculate group sales and price change based on group sales and Group Sens.
        group_sales = sum(purchases[g] for g in df[df['Group'] == group]['ID'])
        group_sensitivity = df.loc[df['ID'] == drink_id, 'Group Sens.'].iloc[0]
        if group_sales > 0:
            group_sales_factor = num_purchases / group_sales
            group_price_change = group_sales_factor * group_sensitivity
        else:
            group_price_change = 0

        # Calculate price change based on random factor and Rand. Sens.
        random_price_change = random.uniform(-random_sensitivity, random_sensitivity)

        # Calculate final price change
        price_change = (total_price_change + group_price_change + random_price_change) * price_scaling_factor

        # Update the new price based on the latest price
        new_price = latest_price * (1 + price_change)

        # Ensure the new price stays within the specified range
        minimum_price = df.loc[df['ID'] == drink_id, 'Minimum Price'].iloc[0]
        maximum_price = df.loc[df['ID'] == drink_id, 'Maximum Price'].iloc[0]
        new_price = max(minimum_price, min(new_price, maximum_price))
        new_price = round(new_price, 2)

        # Update the tkinter variable with the new price
        price_vars[drink_id].set(new_price)
        price_vars_str[drink_id].set("{:.2f}".format(new_price))

        # Append the new price to the list and remove the oldest price if the list exceeds 20 items
        prices.append(new_price)
        if len(prices) > 20:
            prices.pop(0)

        updated_prices[drink_id] = new_price

    return updated_prices

def get_price_image():
    width = 1920
    height = 1080
    prices = adjust_prices()

    # Clear existing content on canvas
    canvas.delete("graph")

    # Load and display the background image
    bg_image = Image.open(resource_path("bg.jpg"))
    bg_photo = ImageTk.PhotoImage(bg_image)
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

        name = df.loc[df['ID'] == drink_id, 'Name'].iloc[0]
        short_name = df.loc[df['ID'] == drink_id, 'Short Name'].iloc[0]
        current_price = prices[drink_id]

        # Get the previous price from the list of prices
        previous_price = drink_prices[drink_id][-2] if len(drink_prices[drink_id]) >= 2 else drink_prices[drink_id][-1]

        # Determine if the price has gone up, down, or remained unchanged
        trend = "→" if current_price > previous_price else "←" if current_price < previous_price else ""

        # Set the fill color based on the price trend
        fill_color = "green" if trend == "←" else "red" if trend == "→" else "white"

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
        create_text_with_outline(canvas, column_base + 350, row_position - 23,
                                 anchor="e", text=trend, font=("Josefin Sans", 30), fill=fill_color, angle=90)

        create_text_with_outline(canvas, column_base + 500, row_position - 12,
                                 anchor="e", text=f"{whole_number_part}.", font=("Josefin Sans", 50), fill='white')
        create_text_with_outline(canvas, column_base + 545, row_position + 5,
                                 anchor="e", text=f"{decimal_part_formatted}", font=("Josefin Sans", 25),
                                 fill='white')

        create_text_with_outline(canvas, column_base + 545, row_position - 20,
                                 anchor="e", text=f"DKK", font=("Josefin Sans", 16), fill='white')

        # Graph size
        graph_width = 100
        graph_height = 40
        graph_x = column_base + 240
        graph_y = row_position - 25

        # Create a fig
        fig, ax = plt.subplots(figsize=(graph_width // 5, graph_height // 5))

        # Plot price history on the existing figure
        last_5_prices = drink_prices[drink_id][-5:]
        xs = range(len(last_5_prices))
        ys = last_5_prices
        ax.plot(xs, ys, marker='', linewidth=130, color='black')
        ax.plot(xs, ys, marker='', linewidth=70, color='white')

        minimum_price = df.loc[df['ID'] == drink_id, 'Minimum Price'].iloc[0]
        maximum_price = df.loc[df['ID'] == drink_id, 'Maximum Price'].iloc[0]
        ax.set_ylim(minimum_price - 3, maximum_price + 3)

        ax.axis('off')
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        plt.tight_layout()

        # Save the figure as a PNG image
        buf = io.BytesIO()
        fig.savefig(buf, format='png', transparent=True)
        buf.seek(0)

        graph_image = Image.open(buf)
        resized_graph_image = graph_image.resize((graph_width, graph_height), Image.Resampling.LANCZOS)

        # Convert the resized image to a Tkinter PhotoImage object
        graph_photo = ImageTk.PhotoImage(resized_graph_image)

        # Overlay the grey box underneath the graph image
        canvas.create_rectangle(graph_x - 2, graph_y - 2, graph_x + graph_width + 4, graph_y + graph_height + 4,
                                fill='gray50', outline='black', width=2, stipple='gray25')

        # Overlay the graph onto the canvas
        canvas.create_image(graph_x, graph_y, image=graph_photo, anchor='nw')
        graph_images[idx] = graph_photo
        plt.close(fig)

    canvas.image = bg_photo
def update_background_image(queue_timer):
    get_price_image()
    if queue_timer and settings_dict["working_mode"] > 1:
        canvas.after(settings_dict["update_frequency"] * 1000, update_background_image, True)

def display_background_image(window):
    global canvas
    # Set window title and geometry
    window.title("Prisoversigt")
    window.geometry("1920x1080")

    # Create canvas
    canvas = tk.Canvas(window, width=1920, height=1080, bg='white')
    canvas.pack()

    # Schedule the update of the background image
    update_background_image(canvas)

    window.mainloop()


def main():
    # Create main Tkinter window
    root = tk.Tk()
    root.title("Main Window")
    root.geometry("1920x1080")
    for index, row in df.iterrows():
        id = str(row['ID'])  # Convert name to string
        price_vars.update({id: tk.IntVar(value=int(row['Starting Price']))})  # Convert to integer
        price_vars_str.update({id: tk.StringVar(value="{:.2f}".format(row['Starting Price']))})
    # Call display_data() to create data display window
    display_data(root)

    # Call display_background_image() to create background image window
    display_background_image(tk.Toplevel(root))

    # Start the main event loop
    root.mainloop()


if __name__ == "__main__":
    main()
