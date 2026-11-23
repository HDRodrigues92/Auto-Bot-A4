import os
import asyncio
from datetime import datetime, timezone, time
import discord
from discord.ext import commands, tasks
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Mini Servidor HTTP para o Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Auto-Fight Bot is online and running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

server_thread = Thread(target=run_server)
server_thread.daemon = True
server_thread.start()
# ---------------------------------------

# Lista fixa de horários diários predefinidos
HORARIOS_DIARIOS = ["18:30", "20:00", "21:00", "22:00", "22:30", "23:00", "00:00"]

class DailyFightView(discord.ui.View):
    def __init__(self, horarios: list):
        super().__init__(timeout=None)
        self.horarios = horarios
        self.inscricoes = {i: set() for i in range(len(horarios))}

        for i, horario in enumerate(horarios):
            button = discord.ui.Button(
                label=f"Inscrever: {horario}",
                style=discord.ButtonStyle.success,
                custom_id=f"daily_spot_{i}",
                row=i // 2
            )
            button.callback = self.criar_callback(i)
            self.add_item(button)

    def criar_callback(self, index: int):
        async def botao_callback(interaction: discord.Interaction):
            user_id = interaction.user.id

            if user_id in self.inscricoes[index]:
                self.inscricoes[index].remove(user_id)
            else:
                self.inscricoes[index].add(user_id)

            await self.atualizar_mensagem(interaction)

        return botao_callback

    async def atualizar_mensagem(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        
        for i, horario in enumerate(self.horarios):
            confirmados = self.inscricoes[i]
            
            if confirmados:
                texto_lista = "\n".join([f"• <@{uid}>" for uid in confirmados])
            else:
                texto_lista = "*Nenhum confirmado ainda.*"

            embed.set_field_at(
                i,
                name=f"🕒 {horario} ({len(confirmados)})",
                value=texto_lista,
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=self)


class AutoFightBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Comandos sincronizados com sucesso!")
        self.publicar_fights_diarias.start()

    # Horário da publicação automática (ex: 10:00 UTC)
    @tasks.loop(time=time(hour=10, minute=0, tzinfo=timezone.utc))
    async def publicar_fights_diarias(self):
        CHANNEL_ID = 1569948200641761320
        
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            return

        view = DailyFightView(HORARIOS_DIARIOS)

        embed = discord.Embed(
            title="⚔️ · Fights do Dia",
            description="Agenda diária de confrontos. Clica nos botões abaixo para te inscreveres nos horários pretendidos.",
            color=discord.Color.dark_theme()
        )

        for horario in HORARIOS_DIARIOS:
            embed.add_field(
                name=f"🕒 {horario}",
                value="*Nenhum confirmado ainda.*",
                inline=False
            )

        embed.set_footer(text="Publicação Automática Diária")
        await channel.send(content="@everyone", embed=embed, view=view)

    @publicar_fights_diarias.before_loop
    async def before_publicar(self):
        await self.wait_until_ready()

bot = AutoFightBot()
bot.run(os.getenv("DISCORD_TOKEN"))