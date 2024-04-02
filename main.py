import tkinter as tk
import pandas as pd

# Load CSV data into a pandas DataFrame
df = pd.read_csv('drinks.csv')
df = df.sort_values('Name')

# Sample dictionary mapping drink names to lists [minimum price, maximum price, starting price, current price]
drink_prices = {row['Name']: [row['Minimum Price'], row['Maximum Price'], row['Starting Price'], row['Starting Price']] for _, row in df.iterrows()}

def display_data():
    # Create window
    window = tk.Tk()
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

    # Create labels for each column (excluding ID)
    labels = ['Navn', 'Min', 'Max', 'Start', 'Nu']
    for i, label in enumerate(labels):
        # Align text to the left for 'Navn' and to the right for other labels
        anchor = "w" if label == 'Navn' else "e"
        label_widget_left = tk.Label(left_frame, text=label, font=('Arial', 22, 'bold'), anchor=anchor)
        label_widget_left.grid(row=0, column=i, padx=30, pady=30, sticky="nsew")

        label_widget_right = tk.Label(right_frame, text=label, font=('Arial', 22, 'bold'), anchor=anchor)
        label_widget_right.grid(row=0, column=i, padx=30, pady=30, sticky="nsew")

    # Display data in two columns (excluding ID)
    count_vars = []
    total = 0  # Variable to store the total cost
    for index, row in df.iterrows():
        name = row['Name']
        minimum_price = row['Minimum Price']
        maximum_price = row['Maximum Price']
        starting_price = row['Starting Price']
        # Fetch current price from the dictionary
        current_price = drink_prices.get(name, [0])[-1]

        # Display the values alternately in left and right frames
        values = [name, minimum_price, maximum_price, starting_price, current_price]
        frame_to_use = left_frame if index % 2 == 0 else right_frame
        for i, value in enumerate(values):
            # Align text to the left for 'Navn' and to the right for other values
            anchor = "w" if i == 0 else "e"
            value_label = tk.Label(frame_to_use, text=value, font=('Arial', 20), wraplength=350, anchor=anchor)
            value_label.grid(row=index // 2 + 1, column=i, padx=30, pady=15, sticky="nsew")
            frame_to_use.grid_columnconfigure(i, weight=1)  # Make columns expandable

        # Add buttons for adding and subtracting counts
        count_var = tk.IntVar(value=0)  # Create IntVar for count
        count_vars.append(count_var)  # Append count variable to the list
        add_button = tk.Button(frame_to_use, text="+", font=('Arial', 16), command=lambda idx=index: add_count(idx))
        add_button.grid(row=index // 2 + 1, column=5, padx=5, pady=15, sticky="nsew")

        subtract_button = tk.Button(frame_to_use, text="-", font=('Arial', 16),
                                    command=lambda idx=index: subtract_count(idx))
        subtract_button.grid(row=index // 2 + 1, column=6, padx=5, pady=15, sticky="nsew")

        # Add count column starting at 0
        count_label = tk.Label(frame_to_use, textvariable=count_var, font=('Arial', 20), anchor="e", width=2)
        count_label.grid(row=index // 2 + 1, column=7, padx=5, pady=15, sticky="nsew")

        # Calculate total cost and update the total variable
        total += count_var.get() * current_price

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

    def add_count(idx):
        # Function to add count when add button is clicked
        count_vars[idx].set(count_vars[idx].get() + 1)
        update_total()

    def subtract_count(idx):
        # Function to subtract count when subtract button is clicked
        current_count = count_vars[idx].get()
        if current_count > 0:
            count_vars[idx].set(current_count - 1)
            update_total()

    def update_total():
        # Function to update the total cost
        nonlocal total
        total = sum(count_vars[idx].get() * drink_prices.get(row['Name'], [])[3] for idx, row in df.iterrows())
        footer_label.config(text="Total: " + "%.2f" % round(total, 2))

    def reset_counts():
        # Function to reset all counts to zero
        for count_var in count_vars:
            count_var.set(0)
        update_total()

    window.mainloop()


# Display the data
display_data()
