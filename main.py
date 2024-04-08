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
                         dtype={"Name": str, "Minimum Price": float, "Maximum Price": float, "Starting Price": float,
                                "Short Name": str, "Group": int, "Total Sensitivity": float, "Group Sensitivity": float,
                                "Random Sensitivity": float, "Price Scaling Factor": float})
    else:
        df.to_csv(path_or_buf=os.path.join(save_path, 'drinks.csv'), index=False)

    if os.path.exists(os.path.join(save_path, 'settings.json')):
        with open(os.path.join(save_path, 'settings.json'), 'r') as f:
            settings_dict = json.load(f)
    else:
        with open(os.path.join(save_path, 'settings.json'), 'w') as f:
            json.dump(settings_dict, f)


save_path = os.path.join(userpaths.get_my_documents(), 'Spruthus-Aktiekurs')
settings_dict = {}
with open(resource_path('settings.json'), 'r') as f:
    json_obj = json.load(f)
    settings_dict.update(**json_obj)

# Load CSV data into a pandas DataFrame
df = pd.read_csv(resource_path('drinks.csv'))
df = df.sort_values('Name')

load_settings()

# Sample dictionary mapping drink names to lists [minimum price, maximum price, starting price, current price]
drink_prices = {row['Name']: [row['Starting Price']] * 20 for _, row in df.iterrows()}
purchases = {row['Name']: 0 for _, row in df.iterrows()}
price_vars = {}

graph_images = [None] * len(df.index)


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
        nonlocal total
        total = sum(count_vars[drink_name].get() * drink_prices.get(drink_name, [])[-1] for drink_name in count_vars)
        footer_label.config(text="Total: " + str(total))

    def reset_counts():
        for drink_name in count_vars:
            purchases[drink_name] += count_vars[drink_name].get()
            count_vars[drink_name].set(0)
        update_total()

    # Create window
    window.title("Product Information")

    # Set window size to 1920x1080
    window.geometry("1920x1080")

    # Header title
    header_label = tk.Label(window, text="Produktoversigt", font=('Arial', 24, 'bold'))
    header_label.pack(padx=10, pady=10)

    # Create parent frame to hold left and right frames
    parent_frame = tk.Frame(window)
    parent_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Create left and right frames
    left_frame = tk.Frame(parent_frame)
    left_frame.pack(side="left", fill="both", expand=True)
    right_frame = tk.Frame(parent_frame)
    right_frame.pack(side="left", fill="both", expand=True)

    # Create labels for each column
    labels = ['Navn', 'Min', 'Max', 'Start', 'Nu']
    for i, label in enumerate(labels):
        # Align text to the left for 'Navn' and to the right for other labels
        anchor = "w" if label == 'Navn' else "e"
        label_widget_left = tk.Label(left_frame, text=label, font=('Arial', 22, 'bold'), anchor=anchor)
        label_widget_left.grid(row=0, column=i, padx=30, pady=30, sticky="nsew")

        label_widget_right = tk.Label(right_frame, text=label, font=('Arial', 22, 'bold'), anchor=anchor)
        label_widget_right.grid(row=0, column=i, padx=30, pady=30, sticky="nsew")

    # Display data in two columns
    count_vars = {}
    total = 0  # Variable to store the total cost
    for index, row in df.iterrows():
        name = row['Name']
        minimum_price = int(row['Minimum Price'])  # Convert to integer
        maximum_price = int(row['Maximum Price'])  # Convert to integer
        starting_price = int(row['Starting Price'])  # Convert to integer
        # Fetch current price from the dictionary
        current_price_var = price_vars[name]

        # Display the values alternately in left and right frames
        values = [name, minimum_price, maximum_price, starting_price, current_price_var]
        frame_to_use = left_frame if index % 2 == 0 else right_frame
        for i, value in enumerate(values):
            # Align text to the left for 'Navn' and to the right for other values
            anchor = "w" if i == 0 else "e"
            if i != 4:
                value_label = tk.Label(frame_to_use, text=f"{value}", font=('Arial', 20), wraplength=350, anchor=anchor)
            else:
                value_label = tk.Label(frame_to_use, textvariable=value, font=('Arial', 20), wraplength=350,
                                       anchor=anchor)
            value_label.grid(row=index // 2 + 1, column=i, padx=30, pady=15, sticky="nsew")
            frame_to_use.grid_columnconfigure(i, weight=1)  # Make columns expandable

        # Add buttons for adding and subtracting counts
        count_var = tk.IntVar(value=0)  # Create IntVar for count
        count_vars[name] = count_var  # Add count variable to the dictionary
        add_button = tk.Button(frame_to_use, text="+", font=('Arial', 16), command=lambda x=name: add_count(x))
        add_button.grid(row=index // 2 + 1, column=5, padx=5, pady=15, sticky="nsew")

        subtract_button = tk.Button(frame_to_use, text="-", font=('Arial', 16),
                                    command=lambda x=name: subtract_count(x))
        subtract_button.grid(row=index // 2 + 1, column=6, padx=5, pady=15, sticky="nsew")

        # Add count column starting at 0
        count_label = tk.Label(frame_to_use, textvariable=count_var, font=('Arial', 20), anchor="e", width=2)
        count_label.grid(row=index // 2 + 1, column=7, padx=5, pady=15, sticky="nsew")

        # Calculate total cost and update the total variable
        total += count_var.get() * current_price_var.get()

        # Adjust row height
        frame_to_use.grid_rowconfigure(index // 2 + 1, minsize=40)  # Set minimum row height to 40 pixels

    # Create footer frame
    footer_frame = tk.Frame(window)
    footer_frame.pack(side="bottom", fill="x", padx=10, pady=10, anchor="center")

    # Add footer for total cost
    footer_label = tk.Label(footer_frame, text="Total: " + str(total), font=('Arial', 24, 'bold'))
    footer_label.pack(padx=10, pady=10)

    # Add button to reset counts
    reset_button = tk.Button(footer_frame, text="Gem", font=('Arial', 24), command=lambda: reset_counts())
    reset_button.pack(padx=10, pady=10)


def display_background_image(window):
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
        purchases = {row['Name']: 0 for _, row in df.iterrows()}
        updated_prices = {}
        total_purchases = sum(purchases.values())

        for drink, prices in drink_prices.items():
            num_purchases = purchases.get(drink, 0)
            latest_price = prices[-1]  # Get the latest price
            total_sensitivity = df.loc[df['Name'] == drink, 'Total Sensitivity'].iloc[0]
            random_sensitivity = df.loc[df['Name'] == drink, 'Random Sensitivity'].iloc[0]
            price_scaling_factor = df.loc[df['Name'] == drink, 'Price Scaling Factor'].iloc[0]

            # Calculate price change based on total sales and Total Sensitivity
            if total_purchases > 0:
                total_sales_factor = num_purchases / total_purchases
                total_price_change = total_sales_factor * total_sensitivity
            else:
                total_price_change = 0

            # Find the group for the current drink
            group = df.loc[df['Name'] == drink, 'Group'].iloc[0]

            # Calculate group sales and price change based on group sales and Group Sensitivity
            group_sales = sum(purchases[g] for g in df[df['Group'] == group]['Name'])
            group_sensitivity = df.loc[df['Name'] == drink, 'Group Sensitivity'].iloc[0]
            if group_sales > 0:
                group_sales_factor = num_purchases / group_sales
                group_price_change = group_sales_factor * group_sensitivity
            else:
                group_price_change = 0

            # Calculate price change based on random factor and Random Sensitivity
            random_price_change = random.uniform(-random_sensitivity, random_sensitivity)

            # Calculate final price change
            price_change = (total_price_change + group_price_change + random_price_change) * price_scaling_factor

            # Update the new price based on the latest price
            new_price = latest_price * (1 + price_change)

            # Ensure the new price stays within the specified range
            minimum_price = df.loc[df['Name'] == drink, 'Minimum Price'].iloc[0]
            maximum_price = df.loc[df['Name'] == drink, 'Maximum Price'].iloc[0]
            new_price = max(minimum_price, min(new_price, maximum_price))
            new_price = round(new_price)

            # Update the tkinter variable with the new price
            price_vars[drink].set(new_price)

            # Append the new price to the list and remove the oldest price if the list exceeds 20 items
            prices.append(new_price)
            if len(prices) > 20:
                prices.pop(0)

            updated_prices[drink] = new_price

        return updated_prices

    def get_price_image(canvas):
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
                                 text="SPRUTHUS AKTIEKURS", font=("Josefin Sans", 50), fill='white')

        side_padding = 100
        row_base = 200
        row_height = 100
        column_width = ((width - side_padding) // 2) // 7

        for idx, (drink, price) in enumerate(prices.items()):
            if idx % 2 == 0:
                column_base = side_padding
            else:
                column_base = (width // 2) + side_padding  # Subtract right_padding from the right column_base
            row = idx // 2

            short_name = df.loc[df['Name'] == drink, 'Short Name'].iloc[0]
            current_price = prices[drink]

            # Get the previous price from the list of prices
            previous_price = drink_prices[drink][-2] if len(drink_prices[drink]) >= 2 else drink_prices[drink][-1]

            # Determine if the price has gone up, down, or remained unchanged
            trend = "→" if current_price > previous_price else "←" if current_price < previous_price else ""

            # Set the fill color based on the price trend
            fill_color = "green" if trend == "←" else "red" if trend == "→" else "white"

            create_text_with_outline(canvas, column_base + column_width * 0, row_base + row_height * row, anchor="w",
                                     text=f"{drink}", font=("Josefin Sans", 36), fill='white')
            create_text_with_outline(canvas, column_base + column_width * 5, row_base + row_height * row, anchor="e",
                                     text=f"{prices[drink]}", font=("Seven Segment", 49), fill='white')
            create_text_with_outline(canvas, column_base + column_width * 5 + 25, row_base + row_height * row + 25,
                                     anchor="w", text=f"{short_name}", font=("Seven Segment", 20), fill='white',
                                     angle=90)
            create_text_with_outline(canvas, column_base + column_width * 5 + 45, row_base + row_height * row - 23,
                                     anchor="e", text=trend, font=("Josefin Sans", 36), fill=fill_color, angle=90)

            # Graph size
            graph_width = 150
            graph_height = 50
            graph_x = column_base + column_width * 2 + 125
            graph_y = row_base + row_height * row - 25

            # Create a fig
            fig, ax = plt.subplots(figsize=(graph_width // 5, graph_height // 5))

            # Plot price history on the existing figure
            last_10_prices = drink_prices[drink][-10:]
            xs = range(len(last_10_prices))
            ys = last_10_prices
            ax.plot(xs, ys, marker='', linewidth=130, color='black')
            ax.plot(xs, ys, marker='', linewidth=70, color='white')

            minimum_price = df.loc[df['Name'] == drink, 'Minimum Price'].iloc[0]
            maximum_price = df.loc[df['Name'] == drink, 'Maximum Price'].iloc[0]
            ax.set_ylim(minimum_price-2, maximum_price+2)

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

    def update_background_image(canvas):
        get_price_image(canvas)
        canvas.after(settings_dict["update_frequency"] * 1000, update_background_image, canvas)

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
        name = str(row['Name'])  # Convert name to string
        price_vars.update({name: tk.IntVar(value=int(row['Starting Price']))})  # Convert to integer
    # Call display_data() to create data display window
    display_data(root)

    # Call display_background_image() to create background image window
    display_background_image(tk.Toplevel(root))

    # Start the main event loop
    root.mainloop()


if __name__ == "__main__":
    main()
