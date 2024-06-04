def format_miss_perms(missing_perms: list[str]) -> str:
	perms = [perm.replace('_',' ') for perm in missing_perms]
	formatted_perms = ', '.join(perms).title()
	return formatted_perms[:-1] if formatted_perms[-1] == ',' else formatted_perms