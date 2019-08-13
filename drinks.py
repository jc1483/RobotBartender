# drinks.py
drink_list = [
	{
		"name": "Gentle Ben",
		"strong": 1,
		"ice": 1,
		"ingredients": {
			"vodka": 2,
			"gin": 2,
			"tequila": 2,
			"oj": 1
		}
	}, {
		"name": "Brady Brew",
		"strong": 1,
		"ice": 1,
		"ingredients": {
			"gingerale": 5,
			"coke": 1,
			"vodka": 8,
			"gin": 8
		}
	}, {
		"name": "Lemmings Leap",
		"strong": 1,
		"ice": 1,
		"ingredients": {
			"vodka": 3,
			"gin": 2,
			"oj": 1,
			"rum": 2
		}
	}, {
		"name": "Orange Flux",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"tequila": 2,
			"vodka": 1,
			"oj": 8,
			"gin": 1
		}
	}, {
		"name": "Caribbean Bliss",
		"strong": 0,
		"ice": 0,
		"ingredients": {
			"vodka": 1,
			"tequila": 1,
			"oj": 4
		}
	}, {
		"name": "Creeper Coke",
		"strong": 0,
		"ice": 0,
		"ingredients": {
			"rum": 4,
			"vodka": 3,
			"coke": 12,
		}
	}, {
		"name": "Darien Librarian",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"coke": 1,
			"whiskey": 1,
			"gingerale": 1
		}
	}, {
		"name": "Gary's Laugh",
		"strong": 0,
		"ice": 0,
		"ingredients": {
			"gin": 1,
			"gingerale": 4,
			"vodka": 1
		}
	}, {
		"name": "Dirty Glass",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"oj": 1,
			"whiskey": 3,
			"cola": 1
		}
	}, {
		"name": "GTV",
		"strong": 1,
		"ice": 1,
		"ingredients": {
			"gin": 1,
			"tequila": 1,
			"vodka": 1
		}
	}, {
		"name": "Have Fun",
		"strong": 1,
		"ice": 1,
		"ingredients": {
			"tequila": 1,
			"coke": 2,
			"whiskey": 1
		}
	}, {
		"name": "Hot Summer Breeze",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"gingerale": 5,
			"coke": 1,
			"vodka": 8,
			"gin": 8
		},
		"add": "Hot Sauce"
	}, {
		"name": "Mexican Water",
		"strong": 1,
		"ice": 0,
		"ingredients": {
			"tequila": 1,
			"vodka": 1,
			"whiskey": 1
		}
	}, {
		"name": "Mir",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"vodka": 1,
			"whiskey": 1,
			"coke": 4
		}
	}, {
		"name": "Power Driver",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"vodka": 1,
			"coke": 2,
			"oj": 1
		}
	}, {
		"name": "The Irish Roundhouse Kick",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"whiskey": 1,
			"vodka": 3,
			"oj": 4
		}
	}, {
		"name": "Water from the Ganges",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"vodka": 2,
			"oj": 1,
			"coke": 4
		}
	}, {
		"name": "Black Bison",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"vodka": 1,
			"coke": 3
		}
	}, {
		"name": "Bob's Moscow Mule",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"vodka": 1,
			"gingerale": 4
		},
		"add": "Lime"
	}, {
		"name": "Bulldog Highball",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"gin": 1,
			"gingerale": 2
		}
	}, {
		"name": "Changuirongo",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"tequila": 1,
			"gingerale": 2
		}
	}, {
		"name": "Rum & Coke",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"rum": 1,
			"coke": 3
		}
	}, {
		"name": "Orange Rum",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"rum": 1,
			"oj": 3
		}
	}, {
		"name": "Whiskey & Coke",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"whiskey": 1,
			"coke": 3
		}
	}, {
		"name": "Crum",
		"strong": 1,
		"ice": 1,
		"ingredients": {
			"whiskey": 1,
			"rum": 2
		}
	}, {
		"name": "Duke's Nightmare",
		"strong": 1,
		"ice": 1,
		"ingredients": {
			"whiskey": 1,
			"tequila": 1
		}
	}, {
		"name": "Gin Sunsplash",
		"strong": 1,
		"ice": 1,
		"ingredients": {
			"gin": 3,
			"oj": 1
		}
	}, {
		"name": "Juicy Volkheimer",
		"strong": 1,
		"ice": 1,
		"ingredients": {
			"vodka": 1,
			"rum": 1
		}
	}, {
		"name": "Neumann",
		"strong": 0,
		"ice": 1,
		"ingredients": {
			"whiskey": 1,
			"oj": 4
		}
	}
]

drink_options = [
	{"name": "Whiskey", "value": "whiskey", "alcohol": 1},
	{"name": "Ginger Ale", "value": "gingerale", "alcohol": 0},
	{"name": "Gin", "value": "gin", "alcohol": 1},
	{"name": "Rum", "value": "rum", "alcohol": 1},
	{"name": "Vodka", "value": "vodka", "alcohol": 1},
	{"name": "Tequila", "value": "tequila", "alcohol": 1},
	{"name": "Coke", "value": "coke", "alcohol": 0},
	{"name": "Orange Juice", "value": "oj", "alcohol": 0}
]
