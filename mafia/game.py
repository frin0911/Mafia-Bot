import os
import asyncio
import random
import sqlite3
import string

from modules.components import *
from datetime import datetime
from nextcord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class MafiaGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}
        self.conn = sqlite3.connect('data.db')
        self.cursor = self.conn.cursor()

    def pick(self, guild, m, p, d):
        def seq(value):
            count = 0
            for u in dummy:
                if value == u:
                    return count
                count += 1

        def select(num, role):
            for i in range(num):
                value = random.choice(dummy)
                users[role].append(value)
                del dummy[seq(value)]

        users = self.data[guild]
        dummy = users['users'][:]
        select(m, 'mafia')
        select(p, 'police')
        select(d, 'doctor')
        users['citizen'] = dummy

    async def end(self, winner, data, thread, msg):
        def gen():
            return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(5))

        embed = nextcord.Embed(title="게임 종료!", color=0x5865F2, description='')
        if winner == 'citizen':
            embed.description = "모든 마피아가 사망하였습니다. 시민팀이 승리하였습니다."
        else:
            embed.description = "모든 시민이 사망하였습니다. 마피아가 승리하였습니다."

        codes = [c[0] for c in self.cursor.execute('SELECT * FROM mafia').fetchall()]
        code = gen()
        while code in codes:
            code = gen()

        data['winner'] = winner
        self.cursor.execute(f'INSERT INTO mafia VALUES ("{code}", "{thread.guild.id}", "{str(data)}")')
        self.conn.commit()

        try:
            doctor = self.bot.get_user(data['doctor'][0]).mention
        except IndexError:
            doctor = '`없음`'

        embed.add_field(name="플레이어",
                        value=f"마피아: {', '.join([self.bot.get_user(m).mention for m in data['mafia']])}\n"
                              f"경찰: {self.bot.get_user(data['police'][0]).mention}\n"
                              f"의사: {doctor}\n"
                              f"시민: {', '.join([self.bot.get_user(c).mention for c in data['citizen']])}\n\n"
                              f"이 게임은 `{os.getenv('PREFIX')}다시보기 {code}` 명령어를 이용하여 다시 볼 수 있습니다.")

        await thread.purge(limit=None)
        await thread.send(embed=embed)
        await msg.edit(embed=embed)

        for u in data['users']:
            user = self.bot.get_user(u)
            await thread.parent.set_permissions(user, send_messages_in_threads=True)

        del self.data[thread.parent.id]
        await asyncio.sleep(60)
        await thread.delete()

    async def check_finish(self, ctx, dead):
        data = self.data[ctx.channel.id]
        for u in data['mafia']:
            if u == dead:
                data['mafia-count'] -= 1
                break

        if len(data['users']) - (data['mafia-count'] + len(data['dead'])) <= data['mafia-count']:
            return 'mafia'
        elif data['mafia-count'] == 0:
            return 'citizen'
        return False

    @commands.command(aliases=['마피아'])
    async def mafia(self, ctx):
        try:
            self.data[ctx.channel.id]
        except KeyError:
            pass
        else:
            embed = nextcord.Embed(title="Mafia", color=0xED4245,
                                   description="이미 이 채널에서 게임이 진행 중입니다.")
            return await ctx.reply(embed=embed)

        start_view = Start(user=ctx.author.id)
        start_embed = nextcord.Embed(title="Mafia", color=0x5865F2,
                                     description="게임을 시작하시겠습니까?")
        start_msg = await ctx.reply(embed=start_embed, view=start_view)

        await start_view.wait()
        await start_msg.delete()
        embed = nextcord.Embed(title="Mafia", color=0xED4245,
                               description="시간이 초과되었습니다. 다시 시도해주세요.")

        if start_view.value is None:
            return await ctx.reply(embed=embed)

        if start_view.value is False:
            embed.description = "게임을 취소하셨습니다."
            return await ctx.reply(embed=embed)

        data = self.data[ctx.channel.id] = {}
        users = data['users'] = []
        data['mafia'], data['police'], data['doctor'], data['citizen'], data['dead'] = [], [], [], [], []
        users.append(ctx.author.id)
        pending_view = Pending(users=users)
        pending_embed = nextcord.Embed(title="Mafia", color=0x5865F2,
                                       description=f"{ctx.author.mention}님이 마피아 게임을 시작하셨습니다. "
                                                   f"참가를 희망하시는 분은 60초 내로 메시지 하단의 이모티콘을 클릭해주세요.\n")
        pending_embed.add_field(name="참가자", value=f"`{len(users)}명`")
        pending_msg = await ctx.send(embed=pending_embed, view=pending_view)
        now = datetime.timestamp(datetime.now())
        until = now + 60
        while now <= until:
            now = datetime.timestamp(datetime.now())
            if pending_view.user not in users:
                users.append(pending_view.user)
                pending_embed.set_field_at(0, name="참가자", value=f"`{len(users)}명`")
                await pending_msg.edit(embed=pending_embed)
            await asyncio.sleep(1)

        await pending_msg.delete()
        user_count = len(users)
        if user_count < 4:
            del self.data[ctx.channel.id]
            embed = nextcord.Embed(title="Mafia", color=0xED4245,
                                   description="인원 수 미달로 게임이 취소되었습니다.")
            return await ctx.reply(embed=embed)

        if user_count >= 24:
            del self.data[ctx.channel.id]
            embed = nextcord.Embed(title="Mafia", color=0xED4245,
                                   description="인원 수 초과로 게임이 취소되었습니다.")
            return await ctx.reply(embed=embed)

        part_embed = nextcord.Embed(title="Mafia", color=0x5865F2,
                                    description=f"`{len(users)}명`이 게임에 참가합니다."
                                                f"\n참가자: {', '.join([f'<@{u}>' for u in users])}\n\n"
                                                f"잠시 후 게임이 시작됩니다.")
        part_msg = await ctx.reply(' '.join([f'<@{u}>' for u in users]), embed=part_embed)
        thread = await part_msg.create_thread(name='마피아', auto_archive_duration=60)
        await thread.trigger_typing()
        await asyncio.sleep(3)

        if user_count == 4:
            self.pick(ctx.channel.id, 1, 1, 0)
        elif user_count == 5:
            self.pick(ctx.channel.id, 1, 1, 1)
        elif user_count in [6, 7]:
            self.pick(ctx.channel.id, 2, 1, 1)
        else:
            self.pick(ctx.channel.id, 3, 1, 1)

        roles_embed = nextcord.Embed(title="직업이 배정되었습니다.", color=0x5865F2,
                                     description=f"마피아: `{len(data['mafia'])}명`\n"
                                                 f"경찰: `{len(data['police'])}명`\n"
                                                 f"의사: `{len(data['doctor'])}명`\n"
                                                 f"시민: `{len(data['citizen'])}명`\n"
                                                 f"\n메시지 하단의 버튼을 눌러 자신의 직업을 확인해주세요.\n"
                                                 f"20초 후 1일차 밤이 됩니다.")
        await thread.send(embed=roles_embed, view=PlayerRoles(data))
        await asyncio.sleep(20)
        await thread.purge(limit=None)
        data['mafia-count'] = len(data['mafia'])
        data['day'] = 1
        data['days'] = {}
        data['days'][1] = {'day': {}, 'night': {}}

        while True:
            for u in users:
                user = self.bot.get_user(u)
                await ctx.channel.set_permissions(user, send_messages_in_threads=False)

            turn_night_embed = nextcord.Embed(title='Mafia', color=0x5865F2, description=f"밤이 되었습니다.")
            await thread.send(embed=turn_night_embed)
            await asyncio.sleep(0.5)

            if data['day'] == 20:
                del self.data[ctx.channel.id]
                embed = nextcord.Embed(title="Mafia", color=0xED4245,
                                       description="비정상적으로 게임이 길어져 강제로 종료되었습니다.")
                return await ctx.reply(embed=embed)

            target = data['days'][data['day']]['night']
            target['mafia'], target['police'], target['doctor'], target['died'] = 0, 0, 0, 0

            night_embed = nextcord.Embed(title=f"{data['day']}일차 - 밤", color=0x5865F2,
                                         description=f"메시지 하단의 버튼을 눌러 능력을 사용해주세요.\n"
                                                     f"\n30초 후 {data['day'] + 1}일차 낮이 됩니다.")
            night_msg = await thread.send(embed=night_embed, view=RoleActivate(self.bot, data))
            await asyncio.sleep(30)
            await night_msg.delete()
            data['day'] += 1

            turn_day_embed = nextcord.Embed(title='Mafia', color=0x5865F2, description=f"낮이 되었습니다.")
            await thread.send(embed=turn_day_embed)
            await asyncio.sleep(0.5)

            dead_embed = nextcord.Embed(title=f"{data['day']}일차 - 낮", color=0x5865F2, description='')
            if not target['mafia'] or target['doctor'] == target['mafia']:
                dead_embed.description = "아무도 사망하지 않았습니다."
            else:
                target['died'] = target['mafia']
                data['dead'].append(target['mafia'])
                dead_embed.description = f"<@{target['mafia']}>님께서 사망하셨습니다."
            await thread.send(embed=dead_embed)

            check = await self.check_finish(ctx, target['mafia'])
            if check:
                return await self.end(check, data, thread, part_msg)

            data['days'][data['day']] = {'day': {}, 'night': {}}

            for u in data['users']:
                if u in data['dead']:
                    continue
                await ctx.channel.set_permissions(self.bot.get_user(u), send_messages_in_threads=True)

            vote = data['days'][data['day']]['day']
            now = datetime.timestamp(datetime.now())
            until = int(now) + 120
            time_voted = vote['time-voted'] = []
            time_view = VoteTime(until, time_voted, data['users'])

            day_embed = nextcord.Embed(title=f"{data['day']}일차 - 낮", color=0x5865F2,
                                       description=f"120초간 자유 토론 시간이 주어집니다.\n"
                                                   f"메시지 하단의 버튼을 눌러 시간을 증가/단축시킬 수 있습니다.")
            day_embed.add_field(name="남은 시간", value=f"<t:{until}:R>")
            day_msg = await thread.send(embed=day_embed, view=time_view)

            while now <= until:
                now = datetime.timestamp(datetime.now())
                if time_view.until != until:
                    until = time_view.until
                    day_embed.set_field_at(0, name="남은 시간", value=f"<t:{until}>")
                    await day_msg.edit(embed=day_embed)
                await asyncio.sleep(1)

            await day_msg.delete()

            vote['voted'], vote['votes'], vote['died'] = [], {}, 0
            vote['votes']['건너뛰기'] = len(data['users']) - len(data['dead'])
            for u in [u for u in data['users'] if u not in data['dead']]:
                vote['votes'][u] = 0

            vote_embed = nextcord.Embed(title=f"{data['day']}일차 - 투표", color=0x5865F2,
                                        description=f"30초 동안 투표로 죽일 사람을 선택해주세요.")
            await thread.send(embed=vote_embed, view=Vote(self.bot, data))
            await asyncio.sleep(30)

            for v in vote['voted']:
                vote['votes']['건너뛰기'] -= 1

            await thread.purge(limit=None)
            total = sorted(vote['votes'].items(), key=lambda k: k[1], reverse=True)
            vote_result = ''
            for t in total:
                name = t[0]
                if t[0] != '건너뛰기':
                    name = f'<@{t[0]}>'
                vote_result += f'{name}: `{t[1]}표`\n'

            vote_result_embed = nextcord.Embed(title=f"{data['day']}일차 - 투표 결과", color=0x5865F2, description='')
            if total[0][1] == total[1][1] or total[0][0] == '건너뛰기':
                vote_result_embed.description = "아무도 사망하지 않았습니다."
            else:
                vote['died'] = total[0][0]
                data['dead'].append(total[0][0])
                vote_result_embed.description = f"<@{total[0][0]}>님께서 사망하셨습니다."
            vote_result_embed.add_field(name="투표 결과", value=vote_result)
            await thread.send(embed=vote_result_embed)

            check = await self.check_finish(ctx, total[0][0])
            if check:
                return await self.end(check, data, thread, part_msg)
            await asyncio.sleep(1)


def setup(bot):
    bot.add_cog(MafiaGame(bot))
