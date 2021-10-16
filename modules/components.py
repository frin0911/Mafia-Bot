import nextcord


class Start(nextcord.ui.View):
    def __init__(self, user: int):
        super().__init__(timeout=60)
        self.value = None
        self.user = user

    @nextcord.ui.button(label="시작", style=nextcord.ButtonStyle.green)
    async def confirm(self, button, interaction):
        if interaction.user.id == self.user:
            self.value = True
            self.stop()

    @nextcord.ui.button(label="취소", style=nextcord.ButtonStyle.red)
    async def cancel(self, button, interaction):
        if interaction.user.id == self.user:
            self.value = False
            self.stop()


class Pending(nextcord.ui.View):
    def __init__(self, users: list):
        super().__init__()
        self.user = users[0]
        self.users = users

    @nextcord.ui.button(label="참가하기", style=nextcord.ButtonStyle.primary)
    async def participate(self, button, interaction):
        if interaction.user.id not in self.users:
            self.user = interaction.user.id
            return await interaction.response.send_message('게임에 참가하셨습니다.', ephemeral=True)


class PlayerRoles(nextcord.ui.View):
    def __init__(self, data: dict):
        super().__init__()
        self.data = data

    @nextcord.ui.button(label='직업 확인하기', style=nextcord.ButtonStyle.primary)
    async def check_role(self, button, interaction):
        embed = nextcord.Embed(title="Mafia", color=0x5865F2, description="")
        if interaction.user.id in self.data['doctor']:
            embed.description = "당신은 `의사`입니다. 매일 밤 마피아로부터 죽임을 당하는 시민을 살릴 수 있습니다."
        elif interaction.user.id in self.data['police']:
            embed.description = "당신은 `경찰`입니다. 매일 밤 선택한 유저가 마피아인지 아닌지를 확인할 수 있습니다."
        elif interaction.user.id in self.data['mafia']:
            embed.description = "당신은 `마피아`입니다. 매일 밤 한 시민을 살해할 수 있습니다."
        elif interaction.user.id in self.data['citizen']:
            embed.description = "당신은 `시민`입니다. 건투를 빕니다."
        else:
            embed.description = "당신은 게임 참가자가 아닙니다."
        return await interaction.response.send_message(embed=embed, ephemeral=True)


class RoleActivate(nextcord.ui.View):
    def __init__(self, bot, data: dict):
        super().__init__()
        self.data = data
        self.bot = bot

    @nextcord.ui.button(label='능력 사용하기', style=nextcord.ButtonStyle.primary)
    async def activate_role(self, button, interaction):
        embed = nextcord.Embed(title="Mafia", color=0x5865F2, description="")
        if interaction.user.id in self.data['dead']:
            embed.description = "사망하셨으므로 능력을 사용할 수 없습니다."
        elif interaction.user.id in self.data['citizen']:
            embed.description = "당신은 시민이므로 능력이 존재하지 않습니다."
        elif interaction.user.id in self.data['mafia']:
            embed.description = "살해할 유저를 선택해주세요."
            return await interaction.response.send_message(embed=embed, ephemeral=True,
                                                           view=UserSelectView(self.bot, self.data))
        elif interaction.user.id in self.data['doctor']:
            embed.description = "살릴 유저를 선택해주세요."
            return await interaction.response.send_message(embed=embed, ephemeral=True,
                                                           view=UserSelectView(self.bot, self.data))
        elif interaction.user.id in self.data['police'] and self.data['day'] != 1:
            embed.description = "조사할 유저를 선택해주세요."
            return await interaction.response.send_message(embed=embed, ephemeral=True,
                                                           view=UserSelectView(self.bot, self.data))
        else:
            embed.description = "당신의 능력은 아직 개방되지 않았거나 게임에 참가하지 않으셨습니다."
        return await interaction.response.send_message(embed=embed, ephemeral=True)


class UserSelectView(nextcord.ui.View):
    def __init__(self, bot, data: dict, night: bool = True):
        super().__init__()
        self.add_item(UserSelect(bot, data, night))


class UserSelect(nextcord.ui.Select):
    def __init__(self, bot, data: dict, night: bool):
        self.data = data
        self.night = night
        self.users = [bot.get_user(u) for u in data['users'] if u not in data['dead']]
        select_options = [nextcord.SelectOption(label=u.name) for u in self.users]
        if night is False:
            select_options.insert(0, nextcord.SelectOption(label='건너뛰기'))
        super().__init__(placeholder="유저를 선택하세요.", min_values=1, max_values=1, options=select_options)

    async def callback(self, interaction):
        if self.night is True:
            user = nextcord.utils.get(self.users, name=self.values[0])
            target = self.data['days'][self.data['day']]['night']

            if interaction.user.id in self.data['mafia']:
                if target['mafia'] and target['mafia'] != user.id:
                    embed = nextcord.Embed(title="Mafia", color=0x5865F2,
                                           description=f"살해대상을 변경하였습니다.")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                target['mafia'] = user.id

            elif interaction.user.id in self.data['doctor']:
                target['doctor'] = user.id

            elif interaction.user.id in self.data['police'] and not target['police']:
                target['police'] = user.id
                embed = nextcord.Embed(title="Mafia", color=0x5865F2, description="")
                if user.id in self.data['mafia']:
                    embed.description = f"{user.mention}님은 마피아입니다."
                else:
                    embed.description = f"{user.mention}님은 마피아가 아닙니다."
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = nextcord.Embed(title="Mafia", color=0xED4245, description="이미 능력을 사용하셨습니다.")
                return await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            vote = self.data['days'][self.data['day']]['day']
            embed = nextcord.Embed(title="Mafia", color=0x5865F2, description="")

            user = None
            if self.values[0] != '건너뛰기':
                user = nextcord.utils.get(self.users, name=self.values[0]).id

            if interaction.user.id not in vote['voted'] and user:
                vote['voted'].append(interaction.user.id)
                vote['votes'][user] += 1
                embed.description = f"<@{user}>님께 투표하였습니다."
            elif interaction.user.id not in vote['voted'] and not user:
                vote['voted'].append(interaction.user.id)
                vote['votes']['건너뛰기'] += 1
                embed.description = "투표 건너뛰기에 투표하였습니다."
            else:
                embed.description = "이미 투표하셨습니다."
            return await interaction.response.send_message(embed=embed, ephemeral=True)


class Vote(nextcord.ui.View):
    def __init__(self, bot, data: dict):
        super().__init__()
        self.bot = bot
        self.data = data

    @nextcord.ui.button(label='투표하기', style=nextcord.ButtonStyle.primary)
    async def button_callback(self, button, interaction):
        if interaction.user.id in self.data['dead']:
            embed = nextcord.Embed(title="Mafia", color=0xED4245, description="사망하셨으므로 투표할 수 없습니다.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        elif interaction.user.id not in self.data['users']:
            embed = nextcord.Embed(title="Mafia", color=0xED4245, description="게임에 참가하지 않으셨으므로 투표할 수 없습니다.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        embed = nextcord.Embed(title="Mafia", color=0x5865F2, description="투표로 죽일 유저를 선택해주세요.")
        return await interaction.response.send_message(embed=embed, ephemeral=True,
                                                       view=UserSelectView(self.bot, self.data, night=False))


class VoteTime(nextcord.ui.View):
    def __init__(self, until: int, voted: list, users: list):
        super().__init__()
        self.until = until
        self.voted = voted
        self.users = users

    @nextcord.ui.button(label="증가", style=nextcord.ButtonStyle.green)
    async def plus(self, button, interaction):
        if interaction.user.id not in self.voted and interaction.user.id in self.users:
            self.voted.append(interaction.user.id)
            self.until += 30
            embed = nextcord.Embed(title='Mafia', color=0x5865F2,
                                   description=f"{interaction.user.mention}님께서 시간을 증가시켰습니다.")
            return await interaction.response.send_message(embed=embed)
        else:
            embed = nextcord.Embed(title='Mafia', color=0xED4245,
                                   description="이미 시간을 증가시키셨거나 게임에 참가하지 않으셨습니다.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="단축", style=nextcord.ButtonStyle.red)
    async def minus(self, button, interaction):
        if interaction.user.id not in self.voted and interaction.user.id in self.users:
            self.voted.append(interaction.user.id)
            self.until -= 30
            embed = nextcord.Embed(title='Mafia', color=0x5865F2,
                                   description=f"{interaction.user.mention}님께서 시간을 단축시켰습니다.")
            return await interaction.response.send_message(embed=embed)
        else:
            embed = nextcord.Embed(title='Mafia', color=0xED4245,
                                   description="이미 시간을 단축시키셨거나 게임에 참가하지 않으셨습니다.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)


class Paginator(nextcord.ui.View):
    def __init__(self, ctx, data: dict):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.data = data
        self.page = 0
        self.value = None

    @nextcord.ui.button(label="이전", style=nextcord.ButtonStyle.primary)
    async def previous(self, button, interaction):
        if self.page > 0 and self.ctx.author.id == interaction.user.id:
            self.page -= 1
            self.value = True
        else:
            self.value = False

    @nextcord.ui.button(label="다음", style=nextcord.ButtonStyle.primary)
    async def next(self, button, interaction):
        if self.page < len(self.data['days']) and self.ctx.author.id == interaction.user.id:
            self.page += 1
            self.value = True
        else:
            self.value = False
