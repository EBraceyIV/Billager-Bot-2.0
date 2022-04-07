import datetime
import random
import discord
from discord.ext import commands
from discord import app_commands
import shelve
import typing

# lore_keeper stores all of the discord.Embed objects for read/write
lore_list = shelve.open("loreKeeper")
all_lore = list(lore_list.keys())
lore_list.close()


# Lore management function
#   action: Add to or remove from lore record, or retrieve a lore entry to alter/display
#   member: Which lore entry to manage
#   embed: The discord.Embed content for the designated lore entry
def lore_access(action, lore_title_, embed_):
    global all_lore
    lore_keeper = shelve.open("loreKeeper")
    if action == "add":
        lore_keeper[lore_title_] = embed_
    elif action == "remove":
        del lore_keeper[lore_title_]
    elif action == "edit":
        lore_access("remove", lore_title_, None)
        lore_access("add", lore_title_, embed_)
    elif action == "retrieve":
        embed = lore_keeper[lore_title_]
        return embed
    all_lore = list(lore_keeper.keys())
    lore_keeper.close()


# Embed constructor to clear up code
#   lore_title: The name of the lore entry
#   lore_desc: The description / content of the lore entry
def embed_init(lore_title, lore_desc):
    # embed is the object that contains all the lore info, can be edited easily as an object
    embed = discord.Embed(title=lore_title,
                          description=lore_desc,
                          color=0x7289da)
    # Generate date the lore was added to add to footer
    date = datetime.date.today()
    # A randomly chosen number is given to the lore entry for show on construction
    embed.set_author(name="Lore Nugget #" + str(random.randint(1000, 9999)))
    embed.set_footer(text="Lore added: " + str(date) + "\n"
                          "More Lore? Tell BBot what needs to be remembered.")
    return embed


class Lore(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Display the requested piece of lore, or a random piece if none is specified
    @app_commands.command(name='lore', description="View some enjoyable server lore.")
    async def lore(self, interaction: discord.Interaction, *, lore_title: typing.Optional[str]):
        lore_title = random.choice(all_lore) if lore_title is None else lore_title
        if lore_title not in all_lore:
            await interaction.response.send_message(
                "You must be from a different timeline (or really bad at spelling) because we don't have "
                "that lore on record.")
            return
        embed = lore_access("retrieve", lore_title, None)
        await interaction.response.send_message(embed=embed)

    # Add a new piece of lore to the records
    @app_commands.command(name="add_lore",
                          description="Add a new piece of lore to the records. Title and then description.")
    async def add_lore(self, interaction: discord.Interaction, lore_title: str, *, lore_description: str):
        # Pass the relevant info to the embed builder
        embed = embed_init(lore_title, lore_description)
        # The lore is stored as the type embed in the shelf file
        lore_access("add", lore_title, embed)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="edit_lore",
                          description="Edit a piece of lore on the records.")
    async def edit_lore(self, interaction: discord.Interaction, lore_title: str, edit_field: str, edit_content: str):
        if lore_title not in all_lore:
            await interaction.response.send_message("Can't find that lore!")
            return
        # Load the embed object once we know it exists so it can be edited
        embed = lore_access("retrieve", lore_title, None)

        # if edit_field.lower() == "title":

    @lore.autocomplete("lore_title")
    @edit_lore.autocomplete("lore_title")
    async def lore_title_autocomplete(self,
                                      interaction: discord.Interaction,
                                      current: str) -> list[app_commands.Choice[str]]:
        lore_titles = all_lore
        return [app_commands.Choice(name=lore_title, value=lore_title)
                for lore_title in lore_titles if current.lower() in lore_title.lower()]

    @edit_lore.autocomplete("edit_field")
    async def edit_field_autocomplete(self,
                                      interaction: discord.Interaction,
                                      current: str) -> list[app_commands.Choice[str]]:
        edit_fields = ["title", "content", "number"]
        return [app_commands.Choice(name=edit_field, value=edit_field)
                for edit_field in edit_fields if current.lower() in edit_field.lower()]


async def setup(bot):
    await bot.add_cog(Lore(bot), guild=discord.Object(id=627279552481067030))