import asyncio
import os
import sqlite3
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv
from ast import literal_eval
from modules.components import Paginator

load_dotenv()


class MafiaReplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cursor = sqlite3.connect('data.db').cursor()

    async def get_list(self, ctx):
        results = self.cursor.execute(f'SELECT * FROM mafia ORDER BY code').fetchall()
        if not results:
            embed = nextcord.Embed(title="Mafia", color=0xED4245,
                                   description="저장된 게임이 없습니다.")
            return await ctx.reply(embed=embed)

        content = '```\n'
        for r in results:
            content += f'{r[0]}\n'

        embed = nextcord.Embed(title="게임 목록", color=0x5865F2, description=content + '```')
        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        return await ctx.reply(embed=embed)

    @commands.command(aliases=['다시보기'])
    async def replay(self, ctx, code: str = None):
        if not code:
            embed = nextcord.Embed(title="Mafia", color=0xED4245,
                                   description=f"사용법: `{os.getenv('PREFIX')}다시보기 [목록 또는 게임 코드]`")
            return await ctx.reply(embed=embed)

        if code == '목록':
            return await self.get_list(ctx)

        result = self.cursor.execute(f'SELECT * FROM mafia WHERE code = "{code}"').fetchone()
        if not result:
            embed = nextcord.Embed(title="Mafia", color=0xED4245,
                                   description="올바르지 않은 코드입니다.")
            return await ctx.reply(embed=embed)

        data = result[2]
        temp = literal_eval(data)
        count = 1
        for u in temp['users']:
            data = data.replace(str(u), f"'플레이어 {count}'")
            count += 1
        data = literal_eval(data)

        winner = {
            'citizen': '시민',
            'mafia': '마피아'
        }

        def get_fields(e):
            e.add_field(name="승리", value=winner[data['winner']], inline=False)
            e.add_field(name="참가자", value=f"{len(data['users'])}명")
            e.add_field(name="플레이 일 수", value=f"{len(data['days'])}일")
            e.add_field(name="마피아", value='`' + '`, `'.join(data['mafia']) + '`', inline=False)
            e.add_field(name="경찰", value=f"`{data['police'][0]}`", inline=False)
            if data['doctor']:
                e.add_field(name="의사", value=f"`{data['doctor'][0]}`", inline=False)
            e.add_field(name="시민", value='`' + '`, `'.join(data['citizen']) + '`', inline=False)

        embed = nextcord.Embed(title=f"요약 - `{code}`", color=0x5865F2)
        get_fields(embed)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        view = Paginator(ctx, data)
        msg = await ctx.reply(embed=embed, view=view)

        def get(t, p=False):
            value = '없음'
            if t:
                if p:
                    value = '`, `'.join(t)
                else:
                    value = t
            return value

        page = -1
        while True:
            await asyncio.sleep(0.1)
            if view.page == page or not view.value:
                continue
            page = view.page
            embed.clear_fields()

            if page == 0:
                embed.title = f"요약 - `{code}`"
                get_fields(embed)
            else:
                day = data['days'][page]
                embed.title = f"{page}일차"
                if day['day']:
                    d = day['day']

                    vote_result = '```\n'
                    for r in d['votes']:
                        vote_result += f"{r}: {d['votes'][r]}표\n"

                    embed.add_field(name="낮", inline=False,
                                    value=f"사망자: `{get(d['died'])}`\n"
                                          f"토론 시간 투표 참여자: `{get(d['time-voted'], True)}`\n"
                                          f"투표 참여자: `{get(d['voted'], True)}`\n\n"
                                          f"투표 결과: {vote_result}```")

                if day['night']:
                    n = day['night']

                    embed.add_field(name="밤", inline=False,
                                    value=f"사망자: `{get(n['died'])}`\n"
                                          f"마피아 지목: `{get(n['mafia'])}`\n"
                                          f"경찰 지목: `{get(n['police'])}`\n"
                                          f"의사 지목: `{get(n['doctor'])}`")
            await msg.edit(embed=embed)


def setup(bot):
    bot.add_cog(MafiaReplay(bot))
