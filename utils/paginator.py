from discord import ui, Interaction, InteractionMessage, ButtonStyle, utils
from typing import List, TypeVar, Optional, Union, Generic

T = TypeVar('T')

class ChunkedPaginator(ui.View, Generic[T]):
	index = 0
	message: Optional[InteractionMessage] = None
	def __init__(self, itr: List[T], timeout: Optional[Union[int,float]] = None):
		self.chunked = list(utils.as_chunks(itr,8))
		super().__init__(timeout=timeout)
		self.edit_children()

	def edit_children(self):
		self.go_first.disabled = self.index == 0
		self.go_back.disabled = self.index == 0
		self.go_foward.disabled = self.index == len(self.chunked)-1
		self.go_last.disabled = self.index == len(self.chunked)-1

	async def edit_embed(self, interaction: Interaction):
		...

	@ui.button(label='<<',style=ButtonStyle.primary)
	async def go_first(self, interaction: Interaction, button: ui.Button):
		self.index = 0
		await self.edit_embed(interaction)

	@ui.button(label='<',style=ButtonStyle.secondary)
	async def go_back(self, interaction: Interaction, button: ui.Button):
		self.index -= 1
		await self.edit_embed(interaction)

	@ui.button(label='>',style=ButtonStyle.secondary)
	async def go_foward(self, interaction: Interaction, button: ui.Button):
		self.index += 1
		await self.edit_embed(interaction)

	@ui.button(label='>>',style=ButtonStyle.primary)
	async def go_last(self, interaction: Interaction, button: ui.Button):
		self.index = len(self.chunked)-1
		await self.edit_embed(interaction)
	
	async def on_timeout(self):
		if self.message:
			await self.message.edit(view=None)