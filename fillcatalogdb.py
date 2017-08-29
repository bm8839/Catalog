"""This file was used to initially populate the catalog database."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from catalogdb_setup import Base, User, Category, Item

engine = create_engine('sqlite:///catalog.db')

"""Bind the engine to the metadata of the Base class so that the
declaratives can be accessed through a DBSession instance
"""
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
"""A DBSession() instance establishes all conversations with the database
and represents a "staging zone" for all the objects loaded into the
database session object. Any change made against the objects in the
session won't be persisted into the database until you call
session.commit(). If you're not happy about the changes, you can
revert all of them back to the last commit by calling
session.rollback()
"""
session = DBSession()


# Create dummy user
User1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')  # noqa
session.add(User1)
session.commit()


# Baseball category and items
category1 = Category(user_id=1, name="Baseball")

session.add(category1)
session.commit()

item1 = Item(user_id=1, name="Glove",
             description="Catcher's mitt made by Wilson",
             category_name=category1.name)

session.add(item1)
session.commit()

item2 = Item(user_id=1, name="Bat",
             description="34-inch Aluminum Louisville Slugger",
             category=category1)

session.add(item2)
session.commit()

item3 = Item(user_id=1, name="Ball",
             description="Major League official hardball",
             category=category1)

session.add(item3)
session.commit()


# Football category and items
category2 = Category(user_id=1, name="Football")

session.add(category2)
session.commit()


item1 = Item(user_id=1, name="Helmet",
             description="Plastic with facemask and a lot of padding",
             category=category2)

session.add(item1)
session.commit()

item2 = Item(user_id=1, name="Shoulder Pads",
             description="Hard plastic but padded on the inside for comfort",
             category=category2)

session.add(item2)
session.commit()


# Basketball category and items
category3 = Category(user_id=1, name="Basketball")

session.add(category3)
session.commit()

item1 = Item(user_id=1, name="Shoes",
             description="Converse sneakers made for quickness",
             category=category3)

session.add(item1)
session.commit()

item2 = Item(user_id=1, name="Goal",
             description="Regulation height with mobile base",
             category=category3)

session.add(item2)
session.commit()
