"""
Wiki Export Handler

Overview
===============================================================================

+----------+------------------------------------------------------------------+
| Path     | PyPoE/cli/exporter/wiki/parser.py                                |
+----------+------------------------------------------------------------------+
| Version  | 1.0.0a0                                                          |
+----------+------------------------------------------------------------------+
| Revision | $Id$                  |
+----------+------------------------------------------------------------------+
| Author   | Omega_K2                                                         |
+----------+------------------------------------------------------------------+

Description
===============================================================================

Base classes and related functions for Wiki Export Handlers.

Agreement
===============================================================================

See PyPoE/LICENSE

Documentation
===============================================================================

Classes
-------------------------------------------------------------------------------

.. autoclass:: BaseParser

.. autoclass:: WikiCondition

.. autoclass:: TagHandler

Functions
-------------------------------------------------------------------------------

.. autofunction:: find_template

.. autofunction:: format_result_rows

.. autofunction:: make_inter_wiki_links

.. autofunction:: parse_and_handle_description_tags
"""

# =============================================================================
# Imports
# =============================================================================

# Python
import re
import warnings
from collections import OrderedDict
from functools import partial

# self
from PyPoE.cli.core import console, Msg
from PyPoE.cli.exporter import config
from PyPoE.poe.constants import MOD_DOMAIN, WORDLISTS
from PyPoE.poe.text import parse_description_tags
from PyPoE.poe.file.dat import RelationalReader, set_default_spec
from PyPoE.poe.file.translations import (
    TranslationFileCache,
    MissingIdentifierWarning,
    get_custom_translation_file,
    install_data_dependant_quantifiers,
)
from PyPoE.poe.file.ot import OTFileCache
from PyPoE.poe.sim.mods import get_translation_file_from_domain

# =============================================================================
# Globals
# =============================================================================

__all__ = [
    'BaseParser',
    'WikiCondition',
    'TagHandler',

    'find_template',
    'format_result_rows',
    'make_inter_wiki_links',
    'parse_and_handle_description_tags',
]

DEFAULT_INDENT = 32

_inter_wiki_map = (
    #
    # Attibutes
    #
    ('Dexterity', {'link': 'Dexterity'}),
    ('Intelligence', {'link': 'Intelligence'}),
    ('Strength', {'link': 'Strength'}),
    #
    # Offense stats
    #
    ('Accuracy Rating', {'link': 'Accuracy Rating'}),
    ('Accuracy', {'link': 'Accuracy'}),
    ('Attack Speed', {'link': 'Attack Speed'}),
    ('Cast Speed', {'link': 'Cast Speed'}),
    ('Critical Strike Chance', {'link': 'Critical Strike Chance'}),
    ('Critical Strike Multiplier', {'link': 'Critical Strike Multiplier'}),
    ('Critical Strike', {'link': 'Critical Strike'}),
    ('Movement Speed', {'link': 'Movement Speed'}),
    ('Leech', {'link': 'Leech'}), # Life Leech, Mana Leech
    ('Life', {'link': 'Life'}),
    ('Mana Reservation', {'link': 'Mana Reservation'}),
    ('Mana', {'link': 'Mana'}),
    # Just damage
    #('Damage', {'link': 'Damage'}),
    #
    # Defenses
    #
    ('Armour Rating', {'link': 'Armour Rating'}),
    ('Armour', {'link': 'Armour'}),
    ('Energy Shield', {'link': 'Energy Shield'}),
    ('Evasion Rating', {'link': 'Evasion Rating'}),
    ('Evasion', {'link': 'Evasion'}),
    ('Spell Block', {'link': 'Spell Block'}),
    ('Block', {'link': 'Block'}),
    ('Spell Dodge', {'link': 'Spell Dodge'}),
    ('Dodge', {'link': 'Dodge'}),
    #
    ('Chaos Resistance(?:|s)', {'link': 'Chaos Resistance'}),
    ('Cold Resistance(?:|s)', {'link': 'Cold Resistance'}),
    ('Fire Resistance(?:|s)', {'link': 'Fire Resistance'}),
    ('Lightning Resistance(?:|s)', {'link': 'Lightning Resistance'}),
    ('Elemental Resistance(?:|s)', {'link': 'Elemental Resistance'}),
    #
    # Buffs
    #

    # Charges
    ('Endurance Charge(?:|s)', {'link': 'Endurance Charge'}),
    ('Frenzy Charge(?:|s)', {'link': 'Frenzy Charge'}),
    ('Power Charge(?:|s)', {'link': 'Power Charge'}),

    # Friendly
    ('Rampage', {'link': 'Rampage'}),

    # Hostile
    ('Corrupted Blood', {'link': 'Corrupted Blood'}),

    #
    # Misc stats
    #

    ('Character Size', {'link': 'Character Size'}),

    #
    # Skills
    #
    ('Abyssal Cry', {'link': 'Abyssal Cry'}),
    ('Ancestral Protector', {'link': 'Ancestral Protector'}),
    ('Ancestral Warchief', {'link': 'Ancestral Warchief'}),
    ('Anger', {'link': 'Anger'}),
    ('Animate(?:|d) Guardian', {'link': 'Animate Guardian'}),
    ('Animate(?:|d) Weapon', {'link': 'Animate Weapon'}),
    ('(?:Arc | Arc)', {'link': 'Arc'}),
    ('Arctic Armour', {'link': 'Arctic Armour'}),
    ('Arctic Breath', {'link': 'Arctic Breath'}),
    ('Assassin\'s Mark', {'link': 'Assassin\'s Mark'}),
    ('Ball Lightning', {'link': 'Ball Lightning'}),
    ('Barrage', {'link': 'Barrage'}),
    ('Bear Trap', {'link': 'Bear Trap'}),
    ('Blade Flurry', {'link': 'Blade Flurry'}),
    ('Blade Trap', {'link': 'Blade Trap'}),
    ('Blade Vortex', {'link': 'Blade Vortex'}),
    ('Bladefall', {'link': 'Bladefall'}),
    ('Blast Rain', {'link': 'Blast Rain'}),
    ('Blight', {'link': 'Blight'}),
    ('Blink Arrow', {'link': 'Blink Arrow'}),
    ('Blood Rage', {'link': 'Blood Rage'}),
    ('Bone Offering', {'link': 'Bone Offering'}),
    ('Burning Arrow', {'link': 'Burning Arrow'}),
    ('Caustic Arrow', {'link': 'Caustic Arrow'}),
    ('Charged Dash', {'link': 'Charged Dash'}),
    ('Clarity', {'link': 'Clarity'}),
    ('Cleave', {'link': 'Cleave'}),
    ('Cold Snap', {'link': 'Cold Snap'}),
    ('Conductivity', {'link': 'Conductivity'}),
    ('Contagion', {'link': 'Contagion'}),
    ('Conversion Trap', {'link': 'Conversion Trap'}),
    ('Convocation', {'link': 'Convocation'}),
    ('Cyclone', {'link': 'Cyclone'}),
    ('Damage Infusion', {'link': 'Damage Infusion'}),
    ('Dark Pact', {'link': 'Dark Pact'}),
    ('Decoy Totem', {'link': 'Decoy Totem'}),
    ('Desecrate', {'link': 'Desecrate'}),
    ('Determination', {'link': 'Determination'}),
    ('Detonate Dead', {'link': 'Detonate Dead'}),
    ('Detonate Mines', {'link': 'Detonate Mines'}),
    ('Devouring Totem', {'link': 'Devouring Totem'}),
    ('Discharge', {'link': 'Discharge'}),
    ('Discipline', {'link': 'Discipline'}),
    ('Dominating Blow', {'link': 'Dominating Blow'}),
    ('Doom Arrow', {'link': 'Doom Arrow'}),
    ('Double Strike', {'link': 'Double Strike'}),
    ('Dual Strike', {'link': 'Dual Strike'}),
    ('Earthquake', {'link': 'Earthquake'}),
    ('Elemental Hit', {'link': 'Elemental Hit'}),
    ('Elemental Weakness', {'link': 'Elemental Weakness'}),
    ('Enduring Cry', {'link': 'Enduring Cry'}),
    ('Energy Beam', {'link': 'Energy Beam'}),
    ('Enfeeble', {'link': 'Enfeeble'}),
    ('Essence Drain', {'link': 'Essence Drain'}),
    ('Ethereal Knives', {'link': 'Ethereal Knives'}),
    ('Explosive Arrow', {'link': 'Explosive Arrow'}),
    ('Fire Nova Mine', {'link': 'Fire Nova Mine'}),
    ('Fire Trap', {'link': 'Fire Trap'}),
    ('Fire Weapon', {'link': 'Fire Weapon'}),
    ('Fireball', {'link': 'Fireball'}),
    ('Firestorm', {'link': 'Firestorm'}),
    ('Flame Dash', {'link': 'Flame Dash'}),
    ('Flame Surge', {'link': 'Flame Surge'}),
    ('Flame Totem', {'link': 'Flame Totem'}),
    ('Flameblast', {'link': 'Flameblast'}),
    ('Flammability', {'link': 'Flammability'}),
    ('Flesh Offering', {'link': 'Flesh Offering'}),
    ('Flicker Strike', {'link': 'Flicker Strike'}),
    ('Freeze Mine', {'link': 'Freeze Mine'}),
    ('Freezing Pulse', {'link': 'Freezing Pulse'}),
    ('Frenzy', {'link': 'Frenzy'}),
    ('Frostbolt', {'link': 'Frostbolt'}),
    ('Frost Blades', {'link': 'Frost Blades'}),
    ('Frost Bomb', {'link': 'Frost Bomb'}),
    ('Frost Wall', {'link': 'Frost Wall'}),
    ('Frostbite', {'link': 'Frostbite'}),
    ('Glacial Cascade', {'link': 'Glacial Cascade'}),
    ('Glacial Hammer', {'link': 'Glacial Hammer'}),
    ('Grace', {'link': 'Grace'}),
    ('Ground Slam', {'link': 'Ground Slam'}),
    ('Haste', {'link': 'Haste'}),
    ('Hatred', {'link': 'Hatred'}),
    ('Heavy Strike', {'link': 'Heavy Strike'}),
    ('Herald of Ash', {'link': 'Herald of Ash'}),
    ('Herald of Blood', {'link': 'Herald of Blood'}),
    ('Herald of Ice', {'link': 'Herald of Ice'}),
    ('Herald of Thunder', {'link': 'Herald of Thunder'}),
    ('Ice Crash', {'link': 'Ice Crash'}),
    ('Ice Nova', {'link': 'Ice Nova'}),
    ('Ice Shot', {'link': 'Ice Shot'}),
    ('Ice Spear', {'link': 'Ice Spear'}),
    ('Ice Trap', {'link': 'Ice Trap'}),
    ('Immortal Call', {'link': 'Immortal Call'}),
    ('Incinerate', {'link': 'Incinerate'}),
    ('Infernal Blow', {'link': 'Infernal Blow'}),
    ('Kinetic Blast', {'link': 'Kinetic Blast'}),
    ('Lacerate', {'link': 'Lacerate'}),
    ('Leap Slam', {'link': 'Leap Slam'}),
    ('Lightning Arrow', {'link': 'Lightning Arrow'}),
    ('Lightning Channel', {'link': 'Lightning Channel'}),
    ('Lightning Circle', {'link': 'Lightning Circle'}),
    ('Lightning Strike', {'link': 'Lightning Strike'}),
    ('Lightning Tendrils', {'link': 'Lightning Tendrils'}),
    ('Lightning Trap', {'link': 'Lightning Trap'}),
    ('Lightning Warp', {'link': 'Lightning Warp'}),
    ('Magma Orb', {'link': 'Magma Orb'}),
    ('Mirror Arrow', {'link': 'Mirror Arrow'}),
    ('Molten Shell', {'link': 'Molten Shell'}),
    ('Molten Strike', {'link': 'Molten Strike'}),
    ('Orb of Storms', {'link': 'Orb of Storms'}),
    ('Phase Run', {'link': 'Phase Run'}),
    ('Poacher\'s Mark', {'link': 'Poacher\'s Mark'}),
    ('Portal', {'link': 'Portal'}),
    ('Power Siphon', {'link': 'Power Siphon'}),
    ('Projectile Weakness', {'link': 'Projectile Weakness'}),
    ('Puncture', {'link': 'Puncture'}),
    ('Punishment', {'link': 'Punishment'}),
    ('Purity of Elements', {'link': 'Purity of Elements'}),
    ('Purity of Fire', {'link': 'Purity of Fire'}),
    ('Purity of Ice', {'link': 'Purity of Ice'}),
    ('Purity of Lightning', {'link': 'Purity of Lightning'}),
    ('Rain of Arrows', {'link': 'Rain of Arrows'}),
    ('Raise Spectre', {'link': 'Raise Spectre'}),
    ('Raise Zombie', {'link': 'Raise Zombie'}),
    ('Rallying Cry', {'link': 'Rallying Cry'}),
    ('Reave', {'link': 'Reave'}),
    ('Reckoning', {'link': 'Reckoning'}),
    ('Rejuvenation Totem', {'link': 'Rejuvenation Totem'}),
    ('Righteous Fire', {'link': 'Righteous Fire'}),
    ('Righteous Lightning', {'link': 'Righteous Lightning'}),
    ('Riposte', {'link': 'Riposte'}),
    ('Scorching Ray', {'link': 'Scorching Ray'}),
    ('Searing Bond', {'link': 'Searing Bond'}),
    ('Shadow Blades', {'link': 'Shadow Blades'}),
    ('Shield Charge', {'link': 'Shield Charge'}),
    ('Shock Nova', {'link': 'Shock Nova'}),
    ('Shockwave Totem', {'link': 'Shockwave Totem'}),
    ('Shrapnel Shot', {'link': 'Shrapnel Shot'}),
    ('Siege Ballista', {'link': 'Siege Ballista'}),
    ('Smoke Mine', {'link': 'Smoke Mine'}),
    ('Spark', {'link': 'Spark'}),
    ('Spectral Throw', {'link': 'Spectral Throw'}),
    ('Spirit Offering', {'link': 'Spirit Offering'}),
    ('Split Arrow', {'link': 'Split Arrow'}),
    ('Static Strike', {'link': 'Static Strike'}),
    ('Static Tether', {'link': 'Static Tether'}),
    ('Storm Burst', {'link': 'Storm Burst'}),
    ('Storm Call', {'link': 'Storm Call'}),
    ('(?:Summon |)Chaos Golem(?:|s)', {'link': 'Summon Chaos Golem'}),
    ('(?:Summon |)Flame Golem(?:|s)', {'link': 'Summon Flame Golem'}),
    ('(?:Summon |)Ice Golem(?:|s)', {'link': 'Summon Ice Golem'}),
    ('(?:Summon |)Lightning Golem(?:|s)', {'link': 'Summon Lightning Golem'}),
    ('Summon Raging Spirit', {'link': 'Summon Raging Spirit'}),
    ('Summon Skeleton', {'link': 'Summon Skeleton'}),
    ('(?:Summon |)Stone Golem(?:|s)', {'link': 'Summon Stone Golem'}),
    ('Sunder', {'link': 'Sunder'}),
    ('Sweep', {'link': 'Sweep'}),
    ('Tempest Shield', {'link': 'Tempest Shield'}),
    ('Temporal Chains', {'link': 'Temporal Chains'}),
    ('Tornado Shot', {'link': 'Tornado Shot'}),
    ('Vaal Arc', {'link': 'Vaal Arc'}),
    ('Vaal Burning Arrow', {'link': 'Vaal Burning Arrow'}),
    ('Vaal Clarity', {'link': 'Vaal Clarity'}),
    ('Vaal Cold Snap', {'link': 'Vaal Cold Snap'}),
    ('Vaal Cyclone', {'link': 'Vaal Cyclone'}),
    ('Vaal Detonate Dead', {'link': 'Vaal Detonate Dead'}),
    ('Vaal Discipline', {'link': 'Vaal Discipline'}),
    ('Vaal Double Strike', {'link': 'Vaal Double Strike'}),
    ('Vaal FireTrap', {'link': 'Vaal FireTrap'}),
    ('Vaal Fireball', {'link': 'Vaal Fireball'}),
    ('Vaal Flameblast', {'link': 'Vaal Flameblast'}),
    ('Vaal Glacial Hammer', {'link': 'Vaal Glacial Hammer'}),
    ('Vaal Grace', {'link': 'Vaal Grace'}),
    ('Vaal Ground Slam', {'link': 'Vaal Ground Slam'}),
    ('Vaal Haste', {'link': 'Vaal Haste'}),
    ('Vaal Heavy Strike', {'link': 'Vaal Heavy Strike'}),
    ('Vaal Ice Nova', {'link': 'Vaal Ice Nova'}),
    ('Vaal Immortal Call', {'link': 'Vaal Immortal Call'}),
    ('Vaal Lightning Strike', {'link': 'Vaal Lightning Strike'}),
    ('Vaal Lightning Trap', {'link': 'Vaal Lightning Trap'}),
    ('Vaal Lightning Warp', {'link': 'Vaal Lightning Warp'}),
    ('Vaal Molten Shell', {'link': 'Vaal Molten Shell'}),
    ('Vaal Power Siphon', {'link': 'Vaal Power Siphon'}),
    ('Vaal Rain of Arrows', {'link': 'Vaal Rain of Arrows'}),
    ('Vaal Reave', {'link': 'Vaal Reave'}),
    ('Vaal Righteous Fire', {'link': 'Vaal Righteous Fire'}),
    ('Vaal Spark', {'link': 'Vaal Spark'}),
    ('Vaal Spectral Throw', {'link': 'Vaal Spectral Throw'}),
    ('Vaal Storm Call', {'link': 'Vaal Storm Call'}),
    ('Vaal Summon Skeletons', {'link': 'Vaal Summon Skeletons'}),
    ('Vaal Sweep', {'link': 'Vaal Sweep'}),
    ('Vengeance', {'link': 'Vengeance'}),
    ('Vigilant Strike', {'link': 'Vigilant Strike'}),
    ('Viper Strike', {'link': 'Viper Strike'}),
    ('Vitality', {'link': 'Vitality'}),
    ('Vortex', {'link': 'Vortex'}),
    ('Vulnerability', {'link': 'Vulnerability'}),
    ('Warlord\'s Mark', {'link': 'Warlord\'s Mark'}),
    ('Whirling Blades', {'link': 'Whirling Blades'}),
    ('Wild Strike', {'link': 'Wild Strike'}),
    ('Wither', {'link': 'Wither'}),
    ('Wrath', {'link': 'Wrath'}),
    #
    # Enchantment skills
    #
    ('Commandment of Blades', {'link': 'of Blades'}),
    ('Commandment of Flames', {'link': 'of Flames'}),
    ('Commandment of Force', {'link': 'of Force'}),
    ('Commandment of Frost', {'link': 'of Frost'}),
    ('Commandment of Fury', {'link': 'of Fury'}),
    ('Commandment of Inferno', {'link': 'of Inferno'}),
    ('Commandment of Ire', {'link': 'of Ire'}),
    ('Commandment of Light', {'link': 'of Light'}),
    ('Commandment of Reflection', {'link': 'of Reflection'}),
    ('Commandment of Spite', {'link': 'of Spite'}),
    ('Commandment of Thunder', {'link': 'of Thunder'}),
    ('Commandment of War', {'link': 'of War'}),
    ('Commandment of Winter', {'link': 'of Winter'}),
    ('Commandment of the Grave', {'link': 'of the Grave'}),
    ('Commandment of the Tempest', {'link': 'of the Tempest'}),
    ('Decree of Blades', {'link': 'of Blades'}),
    ('Decree of Flames', {'link': 'of Flames'}),
    ('Decree of Force', {'link': 'of Force'}),
    ('Decree of Frost', {'link': 'of Frost'}),
    ('Decree of Fury', {'link': 'of Fury'}),
    ('Decree of Inferno', {'link': 'of Inferno'}),
    ('Decree of Ire', {'link': 'of Ire'}),
    ('Decree of Light', {'link': 'of Light'}),
    ('Decree of Reflection', {'link': 'of Reflection'}),
    ('Decree of Spite', {'link': 'of Spite'}),
    ('Decree of Thunder', {'link': 'of Thunder'}),
    ('Decree of War', {'link': 'of War'}),
    ('Decree of Winter', {'link': 'of Winter'}),
    ('Decree of the Grave', {'link': 'of the Grave'}),
    ('Decree of the Tempest', {'link': 'of the Tempest'}),
    ('Edict of Blades', {'link': 'of Blades'}),
    ('Edict of Flames', {'link': 'of Flames'}),
    ('Edict of Force', {'link': 'of Force'}),
    ('Edict of Frost', {'link': 'of Frost'}),
    ('Edict of Fury', {'link': 'of Fury'}),
    ('Edict of Inferno', {'link': 'of Inferno'}),
    ('Edict of Ire', {'link': 'of Ire'}),
    ('Edict of Light', {'link': 'of Light'}),
    ('Edict of Reflection', {'link': 'of Reflection'}),
    ('Edict of Spite', {'link': 'of Spite'}),
    ('Edict of Thunder', {'link': 'of Thunder'}),
    ('Edict of War', {'link': 'of War'}),
    ('Edict of Winter', {'link': 'of Winter'}),
    ('Edict of the Grave', {'link': 'of the Grave'}),
    ('Edict of the Tempest', {'link': 'of the Tempest'}),
    ('Word of Blades', {'link': 'of Blades'}),
    ('Word of Flames', {'link': 'of Flames'}),
    ('Word of Force', {'link': 'of Force'}),
    ('Word of Frost', {'link': 'of Frost'}),
    ('Word of Fury', {'link': 'of Fury'}),
    ('Word of Inferno', {'link': 'of Inferno'}),
    ('Word of Ire', {'link': 'of Ire'}),
    ('Word of Light', {'link': 'of Light'}),
    ('Word of Reflection', {'link': 'of Reflection'}),
    ('Word of Spite', {'link': 'of Spite'}),
    ('Word of Thunder', {'link': 'of Thunder'}),
    ('Word of War', {'link': 'of War'}),
    ('Word of Winter', {'link': 'of Winter'}),
    ('Word of the Grave', {'link': 'of the Grave'}),
    ('Word of the Tempest', {'link': 'of the Tempest'}),
    #
    # Support gems
    #
    ('(?:level [0-9]+) Added Chaos Damage', {
        'link': 'Added Chaos Damage Support'}),
    ('(?:level [0-9]+) Added Cold Damage', {
        'link': 'Added Cold Damage Support'}),
    ('(?:level [0-9]+) Added Fire Damage', {
        'link': 'Added Fire Damage Support'}),
    ('(?:level [0-9]+) Added Lightning Damage', {
        'link': 'Added Lightning Damage Support'}),
    ('(?:level [0-9]+) Additional Accuracy', {
        'link': 'Additional Accuracy Support'}),
    ('(?:level [0-9]+) Arcane Surge', {'link': 'Arcane Surge Support'}),
    ('(?:level [0-9]+) Blasphemy', {'link': 'Blasphemy Support'}),
    ('(?:level [0-9]+) Blind', {'link': 'Blind Support'}),
    ('(?:level [0-9]+) Block Chance Reduction', {
        'link': 'Block Chance Reduction Support'}),
    ('(?:level [0-9]+) Blood Magic', {'link': 'Blood Magic Support'}),
    ('(?:level [0-9]+) Bloodlust', {'link': 'Bloodlust Support'}),
    ('(?:level [0-9]+) Brutality', {'link': 'Brutality Support'}),
    ('(?:level [0-9]+) Burning Damage', {'link': 'Burning Damage Support'}),
    ('(?:level [0-9]+) Cast On Critical Strike', {
        'link': 'Cast On Critical Strike Support'}),
    ('(?:level [0-9]+) Cast on Death', {'link': 'Cast on Death Support'}),
    ('(?:level [0-9]+) Cast on Melee Kill', {
        'link': 'Cast on Melee Kill Support'}),
    ('(?:level [0-9]+) Cast when Damage Taken', {
        'link': 'Cast when Damage Taken Support'}),
    ('(?:level [0-9]+) Cast when Stunned', {'link': 'Cast when Stunned Support'}),
    ('(?:level [0-9]+) Chain', {'link': 'Chain Support'}),
    ('(?:level [0-9]+) Chance to Bleed', {'link': 'Chance to Bleed Support'}),
    ('(?:level [0-9]+) Chance to Flee', {'link': 'Chance to Flee Support'}),
    ('(?:level [0-9]+) Chance to Ignite', {'link': 'Chance to Ignite Support'}),
    ('(?:level [0-9]+) Cluster Traps', {'link': 'Cluster Traps Support'}),
    ('(?:level [0-9]+) Cold Penetration', {'link': 'Cold Penetration Support'}),
    ('(?:level [0-9]+) Cold to Fire', {'link': 'Cold to Fire Support'}),
    ('(?:level [0-9]+) Concentrated Effect', {
        'link': 'Concentrated Effect Support'}),
    ('(?:level [0-9]+) Controlled Destruction', {
        'link': 'Controlled Destruction Support'}),
    ('(?:level [0-9]+) Culling Strike', {'link': 'Culling Strike Support'}),
    ('(?:level [0-9]+) Curse On Hit', {'link': 'Curse On Hit Support'}),
    ('(?:level [0-9]+) Damage on Full Life', {
        'link': 'Damage on Full Life Support'}),
    ('(?:level [0-9]+) Deadly Ailments', {'link': 'Deadly Ailments Support'}),
    ('(?:level [0-9]+) Decay', {'link': 'Decay Support'}),
    ('(?:level [0-9]+) Efficacy', {'link': 'Efficacy Support'}),
    ('(?:level [0-9]+) Elemental Focus', {'link': 'Elemental Focus Support'}),
    ('(?:level [0-9]+) Elemental Proliferation', {
        'link': 'Elemental Proliferation Support'}),
    ('(?:level [0-9]+) Empower', {'link': 'Empower Support'}),
    ('(?:level [0-9]+) Endurance Charge on Melee Stun', {
        'link': 'Endurance Charge on Melee Stun Support'}),
    ('(?:level [0-9]+) Enhance', {'link': 'Enhance Support'}),
    ('(?:level [0-9]+) Enlighten', {'link': 'Enlighten Support'}),
    ('(?:level [0-9]+) Elemental Damage with Attacks', {
        'link': 'Elemental Damage with Attacks Support'}),
    ('(?:level [0-9]+) Faster Attacks', {'link': 'Faster Attacks Support'}),
    ('(?:level [0-9]+) Faster Casting', {'link': 'Faster Casting Support'}),
    ('(?:level [0-9]+) Faster Projectiles', {
        'link': 'Faster Projectiles Support'}),
    ('(?:level [0-9]+) Fire Penetration', {'link': 'Fire Penetration Support'}),
    ('(?:level [0-9]+) Fork', {'link': 'Fork Support'}),
    ('(?:level [0-9]+) Fortify', {'link': 'Fortify Support'}),
    ('(?:level [0-9]+) Generosity', {'link': 'Generosity Support'}),
    ('(?:level [0-9]+) Greater Multiple Projectiles', {
        'link': 'Greater Multiple Projectiles Support'}),
    ('(?:level [0-9]+) Hypothermia', {'link': 'Hypothermia Support'}),
    ('(?:level [0-9]+) Ice Bite', {'link': 'Ice Bite Support'}),
    ('(?:level [0-9]+) Increased Area of Effect', {
        'link': 'Increased Area of Effect Support'}),
    ('(?:level [0-9]+) Increased Critical Damage', {
        'link': 'Increased Critical Damage Support'}),
    ('(?:level [0-9]+) Increased Critical Strikes', {
        'link': 'Increased Critical Strikes Support'}),
    ('(?:level [0-9]+) Increased Duration', {
        'link': 'Increased Duration Support'}),
    ('(?:level [0-9]+) Innervate', {'link': 'Innervate Support'}),
    ('(?:level [0-9]+) Ignite Proliferation', {'link': 'Ignite Proliferation Support'}),
    ('(?:level [0-9]+) Iron Grip', {'link': 'Iron Grip Support'}),
    ('(?:level [0-9]+) Iron Will', {'link': 'Iron Will Support'}),
    ('(?:level [0-9]+) Item Quantity', {'link': 'Item Quantity Support'}),
    ('(?:level [0-9]+) Item Rarity', {'link': 'Item Rarity Support'}),
    ('(?:level [0-9]+) Immolate', {'link': 'Immolate Support'}),
    ('(?:level [0-9]+) Knockback', {'link': 'Knockback Support'}),
    ('(?:level [0-9]+) Less Duration', {'link': 'Less Duration Support'}),
    ('(?:level [0-9]+) Lesser Multiple Projectiles', {
        'link': 'Lesser Multiple Projectiles Support'}),
    ('(?:level [0-9]+) Lesser Poison', {'link': 'Lesser Poison Support'}),
    ('(?:level [0-9]+) Life Gain on Hit', {'link': 'Life Gain on Hit Support'}),
    ('(?:level [0-9]+) Life Leech', {'link': 'Life Leech Support'}),
    ('(?:level [0-9]+) Lightning Penetration', {
        'link': 'Lightning Penetration Support'}),
    ('(?:level [0-9]+) Maim', {'link': 'Maim Support'}),
    ('(?:level [0-9]+) Mana Leech', {'link': 'Mana Leech Support'}),
    ('(?:level [0-9]+) Melee Physical Damage', {
        'link': 'Melee Physical Damage Support'}),
    ('(?:level [0-9]+) Melee Splash', {'link': 'Melee Splash Support'}),
    ('(?:level [0-9]+) Minefield', {'link': 'Minefield Support'}),
    ('(?:level [0-9]+) Minion Damage', {'link': 'Minion Damage Support'}),
    ('(?:level [0-9]+) Minion Life', {'link': 'Minion Life Support'}),
    ('(?:level [0-9]+) Minion Speed', {'link': 'Minion Speed Support'}),
    ('(?:level [0-9]+) Minion and Totem Elemental Resistance', {
        'link': 'Minion and Totem Elemental Resistance Support'}),
    ('(?:level [0-9]+) Multiple Traps', {'link': 'Multiple Traps Support'}),
    ('(?:level [0-9]+) Multistrike', {'link': 'Multistrike Support'}),
    ('(?:level [0-9]+) Onslaught', {'link': 'Onslaught Support'}),
    ('(?:level [0-9]+) Physical Projectile Attack Damage', {
        'link': 'Physical Projectile Attack Damage Support'}),
    ('(?:level [0-9]+) Physical to Lightning', {
        'link': 'Physical to Lightning Support'}),
    ('(?:level [0-9]+) Pierce', {'link': 'Pierce Support'}),
    ('(?:level [0-9]+) Point Blank', {'link': 'Point Blank Support'}),
    ('(?:level [0-9]+) Poison', {'link': 'Poison Support'}),
    ('(?:level [0-9]+) Power Charge On Critical', {
        'link': 'Power Charge On Critical Support'}),
    ('(?:level [0-9]+) Ranged Attack Totem', {
        'link': 'Ranged Attack Totem Support'}),
    ('(?:level [0-9]+) Reduced Mana', {'link': 'Reduced Mana Support'}),
    ('(?:level [0-9]+) Remote Mine', {'link': 'Remote Mine Support'}),
    ('(?:level [0-9]+) Return Projectiles', {
        'link': 'Return Projectiles Support'}),
    ('(?:level [0-9]+) Ruthless', {'link': 'Ruthless Support'}),
    ('(?:level [0-9]+) Slower Projectiles', {
        'link': 'Slower Projectiles Support'}),
    ('(?:level [0-9]+) Spell Echo', {'link': 'Spell Echo Support'}),
    ('(?:level [0-9]+) Spell Totem', {'link': 'Spell Totem Support'}),
    ('(?:level [0-9]+) Split Projectiles', {
        'link': 'Split Projectiles Support'}),
    ('(?:level [0-9]+) Stun', {'link': 'Stun Support'}),
    ('(?:level [0-9]+) Swift Affliction', {'link': 'Swift Affliction Support'}),
    ('(?:level [0-9]+) Trap', {'link': 'Trap Support'}),
    ('(?:level [0-9]+) Trap Cooldown', {'link': 'Trap Cooldown Support'}),
    ('(?:level [0-9]+) Trap and Mine Damage', {
        'link': 'Trap and Mine Damage Support'}),
    ('(?:level [0-9]+) Unbound Ailments', {'link': 'Unbound Ailments Support'}),
    ('(?:level [0-9]+) Vile Toxins', {'link': 'Vile Toxins Support'}),
    ('(?:level [0-9]+) Void Manipulation', {
        'link': 'Void Manipulation Support'}),
    #
    # Groups
    #
    ('Physical(?:Skill|Gem)', {'link': 'Physical Skills'}),
    ('Fire (?:Skill|Gem)', {'link': 'Fire Skills'}),
    ('Cold (?:Skill|Gem)', {'link': 'Cold Skills'}),
    ('Lightning (?:Skill|Gem)', {'link': 'Lightning Skills'}),
    ('Chaos (?:Skill|Gem)', {'link': 'Chaos Skills'}),
    ('Area (?:Skill|Gem)', {'link': 'Area Skills'}),
    ('Melee (?:Skill|Gem)', {'link': 'Melee Skills'}),
    ('Bow (?:Skill|Gem)', {'link': 'Bow Skills'}),
    ('Minion (?:Skill|Gem)', {'link': 'Minion Skills'}),

    #
    # Damage
    #
    # Base types
    ('Chaos Damage', {'link': 'Chaos Damage'}),
    ('Cold Damage', {'link': 'Cold Damage'}),
    ('Fire Damage', {'link': 'Fire Damage'}),
    ('Lightning Damage', {'link': 'Lightning Damage'}),
    ('Physical Damage', {'link': 'Physical Damage'}),
    # Mixed and special
    ('Attack Damage', {'link': 'Attack Damage'}),
    ('Spell Damage', {'link': 'Spell Damage'}),
    ('Elemental Damage', {'link': 'Elemental Damage'}),
    ('Minion Damage', {'link': 'Minion Damage'}),

    #
    # Armour & weapon types
    #

    # Generic
    ('Two Handed Melee Weapon(?:|s)', {'link': 'Two Handed Melee Weapons'}),

    # Armour
    ('Shield(?:|s)', {'link': 'Shield'}),

    # Melee
    ('Axe(?:|s)', {'link': 'Axe'}),
    ('Claw(?:|s)', {'link': 'Claw'}),
    ('Dagger(?:|s)', {'link': 'Dagger'}),
    ('Mace(?:|s)', {'link': 'Mace'}),
    ('Staff|Staves', {'link': 'Staff'}),
    ('Sword(?:|s)', {'link': 'Sword'}),

    # Range
    ('Bow(?:|s)', {'link': 'Bow'}),
    ('Wand(?:|s)', {'link': 'Axe'}),
    #
    # Status
    #

    ('Shock(?:|s|ed)', {'link': 'Shock'}),
    ('Ignite(?:|s|ed)', {'link': 'Ignite'}),
    ('Frozen|Freeze(?:|s)', {'link': 'Freeze'}),
    ('Poison(?:|s|ed)', {'link': 'Poison'}),

    #
    # Misc
    #
    ('Curse(?:|s|ed)', {'link': 'Curse'}),
    ('Socket(?:|s|ed)', {'link': 'Item socket'}),
    ('Recently', {'link': 'Recently'}),
    ('Skill(?:|s)', {'link': 'Skill'}),
    ('Spell(?:|s)', {'link': 'Spell'}),
    ('Attack(?:|s)', {'link': 'Attack'}),
    ('Minion(?:|s)', {'link': 'Minion'}),
    ('Mine(?:|s)', {'link': 'Mine'}),
    ('Totem(?:|s)', {'link': 'Totem'}),
    ('Trap(?:|s)', {'link': 'Trap'}),
    ('Dual Wield(?:|ing)', {'link': 'Dual Wield'}),
    ('Level', {'link': 'Level'}),
    ('PvP', {'link': 'PvP'}),
    ('Hit(?:|s)', {'link': 'Hit'}),
    ('Kill(?:|s)', {'link': 'Kill'}),
    ('Charge(?:|s)', {'link': 'Charge'}),
)

'''_inter_wiki_re = re.compile(
    r'(?: |^)(?P<text>%s))' % '|'.join([item[0] for item in _inter_wiki_map]),
    re.UNICODE | re.IGNORECASE
)'''
_inter_wiki_re = []
_MAX_RE = 97
for i in range(0, (len(_inter_wiki_map)//_MAX_RE)+1):
    id = i*_MAX_RE
    _inter_wiki_re.append(re.compile(
        r'(?![^\[]*\]\])'
        r'(?: |^)'
        r'(?P<text>%s)'
        r'(?= |$)' %
        '|'.join(['(%s)' % item[0] for item in _inter_wiki_map[id:id+_MAX_RE]]),
        re.UNICODE | re.IGNORECASE ,
    ))

# =============================================================================
# Classes
# =============================================================================


class BaseParser(object):
    """
    :ivar str base_path:

    :ivar rr:
    :type rr: RelationalReader

    :ivar tc:
    :type tc: TranslationFileCache

    :ivar custom:
    :type custom: TranslationFile
    """

    _DETAILED_FORMAT = '<abbr title="%s">%s</abbr>'
    _HIDDEN_FORMAT = '%s (Hidden)'
    _MISSING_MSG = 'Several arguments have not been found:\n%s'

    _files = []
    _translations = []

    def __init__(self, base_path):
        # Make sure to load the appropriate version of the specification
        set_default_spec(version=config.get_option('version'))

        self.base_path = base_path

        opt = {
            'use_dat_value': False,
            'auto_build_index': True,
        }

        # Load rr and translations which will be undoubtedly be needed for
        # parsing
        self.rr = RelationalReader(
            path_or_ggpk=base_path,
            files=self._files,
            read_options=opt,
            raise_error_on_missing_relation=False,
        )
        install_data_dependant_quantifiers(self.rr)
        self.tc = TranslationFileCache(path_or_ggpk=base_path)
        for file_name in self._translations:
            self.tc[file_name]

        self.ot = OTFileCache(path_or_ggpk=base_path)

        self.custom = get_custom_translation_file()

    def _column_index_filter(self, dat_file_name, column_id, arg_list,
                             error_msg=_MISSING_MSG):
        self.rr[dat_file_name].build_index(column_id)

        rows = []
        missing = []

        if column_id in self.rr[dat_file_name].columns_unique:
            func = rows.append
        else:
            func = rows.extend

        for argument in arg_list:
            try:
                func(
                    self.rr[dat_file_name].index[column_id][argument]
                )
            except KeyError:
                missing.append(argument)

        if missing:
            console(
                self._MISSING_MSG % '\n'.join(missing), msg=Msg.warning
            )

        return rows

    def _format_wiki_title(self, title):
        return title.replace('_', '~').replace('~~~', '_~~_~~_')

    def _format_hidden(self, custom):
        return self._HIDDEN_FORMAT % make_inter_wiki_links(custom)

    def _format_detailed(self, custom, ingame):
        return self._DETAILED_FORMAT % (
            ingame,
            make_inter_wiki_links(custom)
        )

    def _get_stats(self, stats, values, mod, translation_file=None):
        if translation_file is None:
            translation_file = get_translation_file_from_domain(mod['Domain'])

        result = self.tc[translation_file].get_translation(
            stats, values, full_result=True
        )

        if mod['Domain'] == MOD_DOMAIN.MONSTER:
            default = self.tc['stat_descriptions.txt'].get_translation(
                result.source_ids, result.source_values, full_result=True
            )

            temp_ids = []
            temp_trans = []

            for i, tr in enumerate(default.found):
                for j, tr2 in enumerate(result.found):
                    if tr.ids != tr2.ids:
                        continue

                    r1 = tr.get_language().get_string(default.values[i])
                    r2 = tr2.get_language().get_string(result.values[j])
                    if r1 and r2 and r1[0] != r2[0]:
                        temp_trans.append(self._format_detailed(r1[0], r2[0]))
                    elif r2 and r2[0]:
                        temp_trans.append(self._format_hidden(r2[0]))
                    temp_ids.append(tr.ids)

                is_missing = True
                for tid in tr.ids:
                    is_missing = is_missing and (tid in result.missing_ids)

                if not is_missing:
                    continue

                r1 = tr.get_language().get_string(default.values[i])
                if r1 and r1[0]:
                    temp_trans.append(self._format_hidden(r1[0]))
                    temp_ids.append(tr.ids)

                for tid in tr.ids:
                    i = result.missing_ids.index(tid)
                    del result.missing_ids[i]
                    del result.missing_values[i]

            index = 0
            for i, tr in enumerate(result.found):
                try:
                    index = temp_ids.index(tr.ids)
                except ValueError:
                    temp_ids.insert(index, tr.ids)
                    temp_trans.insert(index, make_inter_wiki_links(
                        tr.get_language().get_string(result.values[i])[0]
                    ))
                else:
                    pass

            out = temp_trans
        else:
            out = [make_inter_wiki_links(line) for line in result.lines]

        if result.missing_ids:
            custom_result = self.custom.get_translation(
                result.missing_ids,
                result.missing_values,
                full_result=True,
            )

            if custom_result.missing_ids:
                warnings.warn(
                    'Missing translation for ids %s and values %s' % (
                        custom_result.missing_ids, custom_result.missing_values),
                    MissingIdentifierWarning,
                )

            for line in custom_result.lines:
                if line:
                    out.append(self._HIDDEN_FORMAT % line)

        finalout = []
        for line in out:
            if '\n' in line:
                finalout.extend(line.split('\n'))
            else:
                finalout.append(line)

        return finalout


class TagHandler(object):
    """
    Provides tag handlers for use with :func:`parse_description_tags`

    Parameters
    ----------
    tag_handlers : dict[str, callable]
        dictionary containing tags and a callable function for passing to
        :func:`parse_description_tags`
    """

    _IL_FORMAT = '{{il|%s|html=}}'
    _IL_PAGE_FORMAT = '{{il|page=%s|html=}}'
    _C_FORMAT = '{{c|%s|%s}}'

    def __init__(self, rr):
        """
        Parameters
        ----------
        rr : RelationalReader
            RelationalReader instance to use when looking up whether items are
            'real' for linking purposes
        """
        self.rr = rr
        self.rr['BaseItemTypes.dat'].build_index('Name')
        self.rr['Words.dat'].build_index('Text')

        self.tag_handlers = {}
        for key, func in TagHandler.tag_handlers.items():
            self.tag_handlers[key] = partial(func, self)

    def _check_link(self, string):
        items = self.rr['BaseItemTypes.dat'].index['Name'][string]
        if items:
            if items[0]['ItemClassesKey']['Name'] == 'Maps':
                string = self._IL_PAGE_FORMAT % string
            elif string == 'Two-Stone Ring':
                return '[[%s]]' % string
            else:
                string = self._IL_FORMAT % string
        return string

    def _default_handler(self, hstr, parameter, tid):
        return self._C_FORMAT % (tid, self._check_link(hstr))

    def _link_handler(self, hstr, parameter, tid):
        return self._C_FORMAT % (tid, '[[%s]]' % hstr)

    def _unique_handler(self, hstr, parameter):
        words = self.rr['Words.dat'].index['Text'][hstr]
        if words and words[0]['WordlistsKey'] == WORDLISTS.UNIQUE_ITEM:
            hstr = self._IL_FORMAT % hstr
        else:
            hstr = self._check_link(hstr)
        return self._C_FORMAT % ('unique', hstr)

    def _currency_handler(self, hstr, parameter):
        if 'x ' in hstr:
            s = hstr.split('x ', maxsplit=1)
            return self._C_FORMAT % (
                'currency', '%sx %s' % (s[0], self._check_link(s[1]))
            )
        else:
            return self._default_handler(hstr, parameter, 'currency')

    def _pass_through_handler(self, hstr, parameter):
        return hstr

    tag_handlers = {
        'normal': partial(_default_handler, tid='normal'),
        'default': partial(_default_handler, tid='default'),
        'augmented': partial(_default_handler, tid='augmented'),

        'size': _pass_through_handler,
        'smaller': _pass_through_handler,

        'gemitem': partial(_default_handler, tid='gem'),
        'currencyitem': _currency_handler,

        'whiteitem': partial(_default_handler, tid='white'),
        'magicitem': partial(_default_handler, tid='magic'),
        'rareitem': partial(_default_handler, tid='rare'),
        'uniqueitem': _unique_handler,

        'divination': partial(_default_handler, tid='divination'),
        'prophecy': partial(_default_handler, tid='prophecy'),

        'corrupted': partial(_link_handler, tid='corrupted'),
    }


class WikiCondition(object):
    COPY_KEYS = (
        'base_page',
    )

    NAME = NotImplemented
    INDENT = 33
    ADD_INCLUDE = False

    def __init__(self, data, cmdargs):
        self.data = data
        self.cmdargs = cmdargs
        self.template_arguments = None

    def __call__(self, *args, **kwargs):
        page = kwargs.get('page')

        if page is not None:
            # Abuse this so it can be called as "text" and "condition"
            if self.template_arguments is None:
                self.template_arguments = find_template(page.text(), self.NAME)
                if len(self.template_arguments['texts']) == 1:
                    self.template_arguments = None
                    return False

                return True

            for k in self.COPY_KEYS:
                try:
                    self.data[k] = self.template_arguments['kwargs'][k]
                except KeyError:
                    pass

            prefix = ''
            if self.ADD_INCLUDE and '<onlyinclude></onlyinclude>' not in \
                    page.text():
                prefix = '<onlyinclude></onlyinclude>'

            return prefix + self.template_arguments['texts'][0] + \
                   self._get_text() + \
                   ''.join(self.template_arguments['texts'][1:])
        else:
            return self._get_text()

    def _get_text(self):
        return format_result_rows(
            parsed_args=self.cmdargs,
            template_name=self.NAME,
            indent=self.INDENT,
            ordered_dict=self.data,
        )

# =============================================================================
# Functions
# =============================================================================


def format_result_rows(parsed_args, ordered_dict, template_name,
                       indent=DEFAULT_INDENT):
    """
    Formats the given result rows as mediawiki template or module.

    Parameters
    ----------
    parsed_args
        argument parser argument containing the format argument
    ordered_dict : OrderedDict
        OrderedDict instance of the rows to format
    template_name : str
        name of the template
    indent : int
        number of spaces to use for indentation/padding up to the given size

    Returns
    -------
    out : str
        formatted string
    """
    if parsed_args.format == 'template':
        out = ['{{%s\n' % template_name]
        for k, v in ordered_dict.items():
            if v is not None:
                out.append(('|{0: <%s}= {1}\n' % indent).format(k, v))
        out.append('}}')
    elif parsed_args.format == 'module':
        out = ['{']
        for k, v in ordered_dict.items():
            if v is not None:
                out.append('{0} = "{1}", '.format(k, v))
        out[-1] = out[-1].strip(', ')
        out.append('}')
    return ''.join(out)


def make_inter_wiki_links(string):
    """
    Formats the given string according to the predefined inter wiki formatting
    rules and returns it.

    Parameters
    ----------
    string : str
        String to format

    Returns
    -------
    str
        String formatted with inter wiki links
    """

    for i, regex in enumerate(_inter_wiki_re):
        out = []
        last_index = 0
        for match in regex.finditer(string):
            text = match.group('text')
            # Offset by 1 to account for text group
            index = match.groups().index(text, 1)-1
            data = _inter_wiki_map[i*_MAX_RE+index][1]

            out.append(string[last_index:match.start('text')])
            if text == data['link']:
                out.append('[[%s]]' % data['link'])
            else:
                out.append('[[%s|%s]]' % (data['link'], text))

            last_index = match.end('text')

        out.append(string[last_index:])
        string = ''.join(out)

    return string


def find_template(wikitext, template_name):
    """
    Finds a template within wikitext and parses the arguments.

    Parameters
    ----------
    wikitext: string
        wiktext
    template_name: string
        Name of the template to find

    Returns
    -------
    dict[str, object]
        returns a dictionary containing 3 keys:

        texts: list[str]
            text not included in the template itself; each template call
            inbetween
        args: list[str]
            positional arguments passed to the template
        kwargs: OrderedDict[str, str]
            keyword arguments passed to the template in the order they
            appeared in the wikitext

    """
    def f(scanner, result, tid):
        return tid, scanner.match, result

    scanner = re.Scanner([
        # Need to have this look ahead to avoid matching templates that start
        # with the same name.
        (r'{{%s(?=[^\w}\|]*\||}})' % template_name,
            partial(f, tid='template')),
        (r'{{', partial(f, tid='l_brace')),
        (r'}}', partial(f, tid='r_brace')),
        (r'\|', partial(f, tid='pipe')),
        (r'=', partial(f, tid='equals')),
        (r'[{}]{1}', partial(f, tid='single_brace')),
        (r'[^{}\|=]+', partial(f, tid='text')),
    ], re.UNICODE | re.MULTILINE)

    # Returns
    texts = [[], ]
    kw_arguments = OrderedDict()
    arguments = []

    # Loop parameters
    in_template = False
    pre_equal = True
    brace_count = 0
    template_argument = ['', '']

    for tid, match, text in scanner.scan(wikitext)[0]:
        if tid == 'template':
            in_template = True
        elif in_template:
            # r_brace is needed to capture the last argument, as it's not
            # delimited by a pipe
            # It also prevents reaching the second condition in that case
            if tid in ('pipe', 'r_brace') and brace_count == 0:
                pre_equal = True
                if template_argument[1]:
                    kw_arguments[template_argument[0]] = template_argument[1]
                elif template_argument[0]:
                    arguments.append([template_argument[0]])
                template_argument = ['', '']
            elif tid in ('text', 'l_brace', 'r_brace', 'single_brace', 'pipe'):
                index = 0 if pre_equal else 1
                template_argument[index] += text.strip(' \n')
            elif tid == 'equals':
                pre_equal = False

            # Brace counting must be done after the text parsing because
            # the previous brace count is needed up there
            if tid == 'l_brace':
                brace_count += 1
            elif tid == 'r_brace':
                if brace_count == 0:
                    in_template = False
                    texts.append([])
                else:
                    brace_count -= 1
        else:
            texts[-1].append(text)

    # Don't really need the list anymore
    texts = [''.join(t) for t in texts]

    return {'texts': texts, 'args': arguments, 'kwargs': kw_arguments}


def parse_and_handle_description_tags(rr, text):
    """
    Parses and handles description texts

    Parameters
    ----------
    rr : RelationalReader
        RelationalReader instance to pass to TagHandler when parsing
    text : str
        Text which to parse

    Returns
    -------
    str
        Parsed texts with wiki templates/links
    """
    return parse_description_tags(text).handle_tags(
        TagHandler(rr).tag_handlers).replace('\n', '<br>').replace('\r', '')
