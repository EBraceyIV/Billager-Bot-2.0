import asyncio
import datetime
import random
import shelve
import json
import discord
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, tasks
from pathlib import Path


class Auto(commands.Cog, name="Auto"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.callout.start()
        self.score_reset.start()
        self.werewolf.start()
        self.GUILD = str(bot.guilds[0].id)

        # Load the channel to output to from the config
        with open("config.json") as config_json:
            config = json.load(config_json)
        # Extract just the id int from the channel call string (<#XXXXXX>)
        self.wolf_channel = int(config[self.GUILD]["wolf_channel"][2:-1])

    async def update_avatar(self, path):
        with open(path, "rb") as img:
            avatar = img.read()
        await self.bot.user.edit(avatar=avatar)
        img.close()

    # Check every message that comes through and perform a hog-check
    @commands.Cog.listener("on_message")
    async def hog_check(self, message):
        # Do not reply to BB's own messages
        if message.author == self.bot.user:
            return

        # Reply to the secret word with 1/10 chance
        if 'hog' in message.clean_content.lower() and 1 == random.randint(1, 10):
            await message.channel.send('HYPEROMEGAHOGGERS')

    # Weekly Bad Score Callout Post
    # Publicly humiliate whoever has the lowest score with an automated post each Friday
    @tasks.loop(time=datetime.time(23, 0, 0))  # This represents 7:00 P.M. EST (11:00 P.M. UTC)
    async def callout(self):
        # If today is Friday (noted as 5 by isoweekday(), monday-sunday: 1-7), send the callout post
        if datetime.date.isoweekday(datetime.date.today()) == 5:
            callout_channel = 720833461329461347 if self.bot.user.name == "BotTest" else 743616007435976754
            # Sort the current user scores from highest to lowest
            plus_minus = shelve.open("plusMinus")
            score_sorted = sorted(plus_minus.items(), key=lambda x: x[1])
            plus_minus.close()

            # Send our fun little message letting our friend know they should try making better jokes
            callout_post = await self.bot.get_channel(callout_channel).send(
                "This is your weekly Bad Score Callout Post, a public "
                "service brought to you by Billager Bot. This week, " +
                str(score_sorted[0][0]) + " has the worst score so far. All "
                "the way down at a fat " + str(score_sorted[0][1]) + "!")
            # Derive the called out role by name
            # TODO: make this more robust later on
            callout_role = discord.utils.get(self.bot.get_guild(self.bot.guilds[0].id).roles, name="Called Out")
            # Apply the called out role to the user mentioned in the callout post
            await callout_post.mentions[0].add_roles(callout_role)
        else:
            return

    # Reset the scoreboard at midnight after the last callout post of the month
    @tasks.loop(time=datetime.time(4, 0, 0))
    async def score_reset(self):
        # Get the day of the month of the next friday
        next_friday = datetime.date.today() + datetime.timedelta(days=6)
        # If the loop runs on a Saturday (midnight following callout post on Friday evening,
        # and the next Friday's day is a lower number than yesterday's Friday,
        # then reset the scoreboard since that was the last friday of the month.
        if datetime.date.isoweekday(datetime.date.today()) == 6 and datetime.date.today().day - 1 > next_friday.day:
            plus_minus = shelve.open("plusMinus")
            plus_minus.clear()
            plus_minus.close()
        else:
            return

    # On the night of a full moon, Billager becomes the Wolfager
    @tasks.loop(time=datetime.time(1, 0, 0))  # 9 P.M. EST
    async def werewolf(self):
        # Get the day / month / year, prepending a 0 if needed as the url uses leading zeroes
        day = str(datetime.date.today().day) if datetime.date.today().day >= 10 \
            else "0" + str(datetime.date.today().day)
        month = str(datetime.date.today().month) if datetime.date.today().month >= 10 \
            else "0" + str(datetime.date.today().month)
        year = str(datetime.date.today().year)

        # Scrape the HTML from this moon phase website
        url = "https://www.moongiant.com/phase/" + month + "/" + day + "/" + year + "/"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find(id="moonDetails")

        # If the phase of the moon is full, run the werewolf sequence
        if "Full Moon" in results.find_next("span"):
            self.werewolf_run.start()

    # Duration of the werewolf transformation
    @tasks.loop(hours=9, minutes=45, count=1)  # This will add to ten hours, returning BBot to normal at 7 A.M. EST
    async def werewolf_run(self):
        # Update the avatar/presence/nickname and announce Wolfager's arrival
        await self.update_avatar(Path("avatars/wolfager.png"))
        await self.bot.guilds[0].me.edit(nick="Wolfager Bot🪓")
        await self.bot.get_channel(self.wolf_channel).send("**AWOOOOOOOOOO**\nThe *Wolfager* prowls tonight.")
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                                 name="the howls of the pack."))
        self.werewolf_activity.start()

    @tasks.loop(hours=0, minutes=1, count=8)
    async def werewolf_activity(self):
        actions = ["I have the urge to visit London for a big dish of beef chow mein",
                   "c!play werewolves of london",
                   "Hey anyone wanna watch Wolfcop?",
                   "**BARK BARK BARK BARK BARK**",
                   "I have the urge to drink a piña colada at Trader Vic's"]
        await self.bot.get_channel(self.wolf_channel).send(random.choice(actions))
        if self.werewolf.current_loop != 0:
            self.werewolf_activity.change_interval(hours=random.randint(0, 1), minutes=random.randint(0, 45))

    # Billager returns to normal after his Wolfager sabbatical
    @werewolf_run.after_loop
    async def werewolf_done(self):
        # Change the avatar back to normal
        await self.update_avatar(Path("avatars/billager.png"))
        # Stop the werewolf activity loop if it might still be running
        if self.werewolf_activity.is_running():
            self.werewolf_activity.stop()
        # Return the activity and nickname to normal
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing,
                                                                 name="with his axe."))
        await self.bot.guilds[0].me.edit(nick="Billager Bot🪓")
        # Give a buffer for the change to show up in the sidebar / chat log
        await asyncio.sleep(30)
        # Some thoughtful commentary from BBot on the situation
        await self.bot.get_channel(self.wolf_channel).send("*coughs up a filthy werewolf hairball*\n"
                                                           "Isabelle, clear my calendar for the day and book me for "
                                                           "a flea bath at Shampoodle immediately.")


async def setup(bot):
    await bot.add_cog(Auto(bot), guild=discord.Object(id=bot.guilds[0].id))
