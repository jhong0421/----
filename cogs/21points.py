import discord, asyncio
import random
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional

class BlackjackGame:
    def __init__(self):
        self.deck = self._create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False
        self.result = None  # 新增結果屬性
        
    def _create_deck(self):
        return [{'value': v, 'display': d} 
                for _ in range(4)
                for v, d in zip(
                    [11,2,3,4,5,6,7,8,9,10,10,10,10],
                    ['A','2','3','4','5','6','7','8','9','10','J','Q','K']
                )]

    def calculate_hand(self, hand):
        total = sum(card['value'] for card in hand)
        aces = sum(1 for card in hand if card['value'] == 11)
        
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def deal_card(self):
        card = random.choice(self.deck)
        self.deck.remove(card)
        return card

    def dealer_turn(self):
        while self.calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deal_card())

class BlackjackView(ui.View):
    def __init__(self, game, interaction):
        super().__init__(timeout=60)
        self.game = game
        self.interaction = interaction

    async def on_timeout(self):
        self.game.game_over = True
        await self.interaction.edit_original_response(
            content="遊戲超時已結束",
            view=None
        )

    @ui.button(label="要牌", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: ui.Button):
        await self.handle_move(interaction, hit=True)

    @ui.button(label="停牌", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: ui.Button):
        await self.handle_move(interaction, hit=False)

    async def handle_move(self, interaction, hit=True):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("這不是你的遊戲！", ephemeral=True)
        
        if hit:
            self.game.player_hand.append(self.game.deal_card())
            player_total = self.game.calculate_hand(self.game.player_hand)
            
            if player_total > 21:
                self.game.game_over = True
                return await self.end_game(interaction, "玩家爆牌！莊家獲勝")
                
            await self.update_display(interaction)
        else:
            self.game.game_over = True
            await self.end_game(interaction)

    async def end_game(self, interaction, result=None):
        self.game.dealer_turn()
        player_total = self.game.calculate_hand(self.game.player_hand)
        dealer_total = self.game.calculate_hand(self.game.dealer_hand)

        if not result:
            if dealer_total > 21:
                result = "莊家爆牌！玩家獲勝"
            elif player_total > dealer_total:
                result = "玩家獲勝！"
            elif player_total < dealer_total:
                result = "莊家獲勝！"
            else:
                result = "平手！"
        
        # 新增：將結果存儲到遊戲實例中
        self.game.result = result  # <--- 新增此行

        embed = self.create_embed(result, reveal=True)
        await interaction.response.edit_message(embed=embed, view=None)

    async def update_display(self, interaction):
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed)

    def create_embed(self, result=None, reveal=False):
        embed = discord.Embed(
            title="21點遊戲",
            color=discord.Color.gold()
        )
        
        player_cards = " ".join(card['display'] for card in self.game.player_hand)
        dealer_cards = " ".join(card['display'] for card in self.game.dealer_hand) if reveal else f"{self.game.dealer_hand[0]['display']} ?"
        
        embed.add_field(
            name="你的手牌", 
            value=f"{player_cards}\n總分: {self.game.calculate_hand(self.game.player_hand)}",
            inline=False
        )
        
        embed.add_field(
            name="莊家手牌", 
            value=f"{dealer_cards}\n總分: {self.game.calculate_hand(self.game.dealer_hand) if reveal else '??'}",
            inline=False
        )
        
        if result:
            embed.add_field(name="遊戲結果", value=result, inline=False)
            
        return embed

class Game1(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    @app_commands.command(name="21點", description="開始新的21點遊戲")
    async def blackjack(self, interaction: discord.Interaction):
        if interaction.user.id in self.active_games:
            return await interaction.response.send_message("你已經有進行中的遊戲！", ephemeral=True)
        
        game = BlackjackGame()
        game.player_hand = [game.deal_card(), game.deal_card()]
        game.dealer_hand = [game.deal_card(), game.deal_card()]
        self.active_games[interaction.user.id] = game
        
        view = BlackjackView(game, interaction)
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # 等待遊戲結束（通過檢查視圖是否超時或遊戲狀態）
        while not view.is_finished() and not game.game_over:
            await asyncio.sleep(0.5)
        
        # 遊戲結束後記錄結果
        logger = self.bot.get_cog('Logger')
        if logger and hasattr(game, 'result'):  # 確保結果存在
            logger.log_blackjack(
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild.id) if interaction.guild else "DM",
                result=game.result,  # 從遊戲實例獲取結果
                player_score=game.calculate_hand(game.player_hand),
                dealer_score=game.calculate_hand(game.dealer_hand)
            )
        
        self.active_games.pop(interaction.user.id, None)

async def setup(bot):
    await bot.add_cog(Game1(bot))