import tkinter as tk
import pandas as pd
import random

# Load CSV data into a pandas DataFrame
df = pd.read_csv('drinks.csv')
df = df.sort_values('Name')

# Create a dictionary to store the mappings
drink_prices = {}

# Iterate over each row in the DataFrame
for index, row in df.iterrows():
    # Extract information from the row
    name = row["Name"]
    min_price = row["Minimum Price"]
    max_price = row["Maximum Price"]

    # Generate a list of numbers between min and max price
    price_range = [round(random.uniform(min_price, max_price), 2) for _ in range(df.shape[0])]

    # Add the name and price range to the dictionary
    drink_prices[name] = price_range

# Print the dictionary
print(drink_prices)
def adjust_prices(drink_prices, purchases, price_change_factor=0.1, randomness_factor=0.05):
    updated_prices = {}
    total_purchases = sum(purchases.values())

    for drink, prices in drink_prices.items():
        num_purchases = purchases.get(drink, 0)
        avg_price = sum(prices) / len(prices)
        elasticity = df.loc[df['Name'] == drink, 'Price Elasticity'].iloc[0]

        if num_purchases > 0:
            price_change = price_change_factor * (num_purchases / total_purchases) * elasticity
            price_change += random.uniform(-randomness_factor, randomness_factor)
            new_price = avg_price * (1 + price_change)
        else:
            price_change = price_change_factor * (1 / total_purchases) * elasticity
            price_change += random.uniform(-randomness_factor, randomness_factor)
            new_price = avg_price * (1 - price_change)

        updated_prices[drink] = round(new_price, 2)

    return updated_prices

# Example usage:
# Initialize purchases dictionary
purchases = {drink: random.randint(0, 100) for drink in drink_prices.keys()}
# Adjust prices
adjusted_prices = adjust_prices(drink_prices, purchases)
# Print adjusted prices
print(adjusted_prices)
