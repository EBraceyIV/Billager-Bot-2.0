import asyncio
import datetime
import typing
import discord
from discord.ext import commands, tasks
from discord import app_commands
import typing
import json


class PollEmbed(discord.ui.Modal, title="Build-A-Poll: Embed Title & Description"):
    # TextInputs to accept the lore title and description, both required
    title_ = discord.ui.TextInput(label="Title:", style=discord.TextStyle.short, required=True)
    description = discord.ui.TextInput(label="Description:", style=discord.TextStyle.long, required=True)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()


class PollModal(discord.ui.Modal, title="Build-A-Poll: Choices"):
    # Get poll options, minimum 2, max 4
    opt1 = discord.ui.TextInput(label="Option 1️⃣:", style=discord.TextStyle.short, required=True)
    opt2 = discord.ui.TextInput(label="Option 2️⃣:", style=discord.TextStyle.short, required=True)
    opt3 = discord.ui.TextInput(label="Option 3️⃣:", style=discord.TextStyle.short, required=False)
    opt4 = discord.ui.TextInput(label="Option 4️⃣:", style=discord.TextStyle.short, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()


class ColorModal(discord.ui.Modal, title="Build-A-Poll: Color"):
    # Pick a color to highlight the poll with
    # list_color = discord.ui.Select(options=[discord.SelectOption(label="Red", value=discord.Color.red().value),
    #                                         discord.SelectOption(label="Blue", value=discord.Color.blue().value),
    #                                         discord.SelectOption(label="Green", value=discord.Color.green().value)],
    #                                max_values=1)
    hex_color = discord.ui.TextInput(label="Enter RGB code", style=discord.TextStyle.short, required=True,
                                     max_length=6, min_length=6)
    # test = discord.ui.TextInput(label="TEST", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()


# UI View
class Buttons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.response = None
        self.title = None
        self.desc = None
        self.opt1 = None
        self.opt2 = None
        self.opt3 = None
        self.opt4 = None
        self.timeout = 300  # View times out after 5 minutes
        self.timed_out = False
        self.embed = None
        self.embed_color = 0

    def build_embed(self):
        embed = discord.Embed(title=self.title,
                              description=self.desc,
                              color=self.embed_color)
        embed.add_field(name="Option 1️⃣:", value=self.opt1, inline=False)
        embed.add_field(name="Option 2️⃣:", value=self.opt2, inline=False)
        if self.opt3 != "":
            embed.add_field(name="Option 3️⃣:", value=self.opt3, inline=False)
        if self.opt4 != "":
            if self.opt3 == "":
                embed.add_field(name="Option 3️⃣:", value=self.opt4, inline=False)
            else:
                embed.add_field(name="Option 4️⃣:", value=self.opt4, inline=False)
        return embed

    # Button to add title and description to the embed
    @discord.ui.button(label="Title & Description", style=discord.ButtonStyle.green, custom_id="title_desc")
    # All three arguments are required, function must pass self.view, interaction, self.item
    async def embed_setup(self, interaction: discord.Interaction, button: discord.Button):
        modal = PollEmbed()
        await interaction.response.send_modal(modal)
        await modal.wait()

        self.title = modal.title_.value
        self.desc = modal.description.value
        self.embed = self.build_embed()
        self.color.disabled = False

        await interaction.edit_original_message(embed=self.embed, view=self)

    # Button to add choices for the poll
    @discord.ui.button(label="Choices", style=discord.ButtonStyle.green, custom_id="choices")
    async def choices(self, interaction: discord.Interaction, button: discord.Button):
        modal = PollModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        self.opt1 = modal.opt1.value
        self.opt2 = modal.opt2.value
        self.opt3 = modal.opt3.value
        self.opt4 = modal.opt4.value

        self.embed = self.build_embed()

        await interaction.edit_original_message(embed=self.embed)

    # Button to add a color to the poll embed
    @discord.ui.button(label="Color", style=discord.ButtonStyle.blurple, disabled=True, custom_id="color")
    async def color(self, interaction: discord.Interaction, button: discord.Button):
        modal = ColorModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        # self.embed_color = int(modal.list_color.values[0])
        self.embed_color = int(modal.hex_color.value, 16)
        self.embed = self.build_embed()

        await interaction.edit_original_message(embed=self.embed)

    # Button to complete and post the poll for usage
    @discord.ui.button(label="Send It!", style=discord.ButtonStyle.grey, custom_id="send_poll")
    async def send_poll(self, interaction: discord.Interaction, button: discord.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    # If poll builder times out, disable the UI and retain the timed_out state for handling
    async def on_timeout(self) -> None:
        self.timed_out = True
        for child in self.children:
            child.disabled = True
        await self.response.edit(view=self)


class Poll(commands.Cog, name="Poll"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.GUILD = str(bot.guilds[0].id)

        # Load the channel to output to from the config
        with open("config.json") as config_json:
            config = json.load(config_json)
        # Extract just the id int from the channel call string (<#XXXXXX>)
        self.poll_channel = int(config[self.GUILD]["poll_channel"][2:-1])

    @app_commands.command(name="poll",
                          description="Start a poll! Enter how long it should last and the options to pick from.")
    async def poll(self, interaction: discord.Interaction):
        view = Buttons()
        embed = discord.Embed(title="Build-A-Poll",
                              description="STILL UNDER DEVELOPMENT, *SOME* FUNCTION GUARANTEED")
        await interaction.response.send_message("What your poll will look like:",
                                                embed=embed,
                                                view=view,
                                                ephemeral=True)
        view.response = await interaction.original_message()
        await view.wait()
        await asyncio.sleep(1)  # Wait just a second for the on_timeout function to run after the view stops

        # If the view timed out, don't post the poll, probably unfinished
        if not view.timed_out:
            poll = await self.bot.get_channel(self.poll_channel).send(embed=view.embed)

            option_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
            for option in range(0, len(poll.embeds[0].fields)):
                await poll.add_reaction(option_emojis[option])

    # @tasks.loop()
    # async def test(self):
    #     print("E?")


async def setup(bot):
    await bot.add_cog(Poll(bot), guild=discord.Object(id=bot.guilds[0].id))
