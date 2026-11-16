import java.nio.file.*;
import java.util.*;
import forge.gui.GuiBase;
import forge.adventure.util.*;
import forge.adventure.data.*;
import forge.localinstance.properties.ForgeConstants;
import forge.model.FModel;
public class Starts {
    static void verifyStarter(forge.deck.Deck deck, Path file, AdventureModes mode, String color) throws Exception {
        Map<String,Integer> expected = new TreeMap<>(), actual = new TreeMap<>();
        String section = "";
        for (String line : Files.readAllLines(file)) {
            if (line.startsWith("[")) section = line.substring(1, line.length() - 1);
            if (!line.matches("[0-9]+ .*")) continue;
            String[] parts = line.split(" ", 2);
            expected.merge(section + "/" + parts[1], Integer.parseInt(parts[0]), Integer::sum);
        }
        int landCount = 0;
        byte basicColors = 0;
        var spells = new ArrayList<forge.item.PaperCard>();
        for (var entry : deck) {
            for (var row : entry.getValue()) {
                var pc = row.getKey();
                actual.merge(entry.getKey() + "/" + pc.getName() + "|" + pc.getEdition() + "|" + pc.getArtIndex(),
                        row.getValue(), Integer::sum);
                if (pc.getRules().getType().isLand()) {
                    landCount += row.getValue();
                    if (pc.getRules().getType().isBasicLand()) basicColors |= pc.getRules().getColorIdentity().getColor();
                } else spells.add(pc);
            }
        }
        if (!expected.equals(actual)) throw new AssertionError("Wrong starter contents: " + file);
        int size = deck.getAllCardsInASinglePool().countAll();
        boolean commander = mode == AdventureModes.Commander;
        if (size != (commander ? 100 : 40) || landCount < (commander ? 35 : 16)
                || landCount > (commander ? 40 : 18)) throw new AssertionError("Mana base " + file);
        int requested = forge.card.MagicColor.fromName(color);
        if ((basicColors & requested) == 0 || Integer.bitCount(basicColors) != (mode == AdventureModes.Pile ? 2 : 1))
            throw new AssertionError("Wrong basic land colors: " + file);
        for (var pc : spells) {
            if (!pc.getRules().canCastWithAvailable(basicColors))
                throw new AssertionError("Missing casting color for " + pc + " in " + file);
        }
    }

    static void battleGroup(List<Map.Entry<String,forge.deck.Deck>> group, boolean commander) {
        var type = commander ? forge.game.GameType.Commander : forge.game.GameType.Constructed;
        for (int i = 0; i < group.size(); i++) {
            var rules = new forge.game.GameRules(type);
            rules.setAppliedVariants(EnumSet.of(type));
            rules.setGamesPerMatch(1);
            rules.setSimTimeout(90);
            var players = new ArrayList<forge.game.player.RegisteredPlayer>();
            for (var entry : List.of(group.get(i), group.get((i+1) % group.size()))) {
                var player = commander ? forge.game.player.RegisteredPlayer.forCommander(entry.getValue())
                        : new forge.game.player.RegisteredPlayer(entry.getValue());
                players.add(player.setPlayer(forge.player.GamePlayerUtil.createAiPlayer(entry.getKey(), players.size())));
            }
            var match = new forge.game.Match(rules, players, "Avatar starters");
            forge.view.SimulateMatch.simulateSingleMatch(match, 0, false);
            if (match.getWinner() == null) throw new AssertionError("Unresolved starter duel " + group.get(i).getKey());
            System.out.println("STARTDUEL " + players.get(0).getPlayer().getName() + " vs " + players.get(1).getPlayer().getName()
                    + " winner=" + match.getWinner().getPlayer().getName() + " turn=" + match.getLastOutcome().getLastTurnNumber());
        }
    }

 public static void main(String[] args) throws Exception {
  TestProfile.require();
        GuiBase.setInterface(new forge.GuiDesktop());
  FModel.initialize(null,null);
  Path settings=Path.of(ForgeConstants.USER_ADVENTURE_DIR,"settings.json");
  if (!settings.toAbsolutePath().normalize().startsWith(Path.of("").toAbsolutePath())) throw new AssertionError(settings);
  Files.createDirectories(settings.getParent());
  Files.writeString(settings,"{\"plane\":\""+args[0]+"\"}");
  Config cfg=Config.instance();
  if(!cfg.getPlane().equals(args[0]) || WorldData.getAllEnemies().size!=464) throw new AssertionError(cfg.getPlane());
  System.out.println("PLANE "+cfg.getPlane()+" "+cfg.getFile("world/enemies.json"));
  if(cfg.hasPreconDecks() || cfg.hasCommanderPreconDecks())throw new AssertionError("Unexpected external precon catalog");
  cfg.getSettingData().useAllCardVariants=Boolean.parseBoolean(args[1]);
  var allowed=Set.of(cfg.getConfigData().allowedEditions);
  int failures=0;
  var groups = new LinkedHashMap<String,LinkedHashMap<String,forge.deck.Deck>>();
  for(var level:cfg.getConfigData().difficulties){
   Current.player().updateDifficulty(level);
   for(var mode:List.of(AdventureModes.Standard,AdventureModes.Constructed,AdventureModes.Pile,AdventureModes.Commander)){
    for(String set:(mode==AdventureModes.Standard?cfg.starterEditions():new String[]{"TLA"}))for(String color:cfg.colorIds()){
     try{
      var deck=cfg.starterDeck(forge.card.ColorSet.fromNames(color.toCharArray()),level,mode,0,FModel.getMagicDb().getEditions().get(set));
      String group = mode.name().toLowerCase(Locale.ROOT);
      if (mode == AdventureModes.Pile || mode == AdventureModes.Constructed) group += "-" + level.name;
      String key = group + "-" + color;
      if (mode == AdventureModes.Pile) {
          if (deck.getMain().countAll() != 60 || !deck.getName().equals("Avatar Pile " + level.name + " " + color))
              throw new AssertionError("Wrong Pile starter " + key + ": " + deck.getName());
      } else verifyStarter(deck, cfg.getFile("decks/starter/" + key + ".dck").file().toPath(), mode, color);
      groups.computeIfAbsent(group, unused -> new LinkedHashMap<>()).putIfAbsent(key, deck);
      var cards=deck.getAllCardsInASinglePool().toFlatList();if(mode==AdventureModes.Commander){
       var leaders=deck.getCommanders(); if(leaders.size()!=1||!leaders.get(0).getRules().canBeCommander()||cards.size()!=100)throw new AssertionError("commander");
       int leader=leaders.get(0).getRules().getColorIdentity().getColor(); var seen=new HashSet<String>(); for(var card:cards)if((card.getRules().getColorIdentity().getColor() & ~leader)!=0||(!card.getRules().getType().isBasicLand() && !seen.add(card.getName())))throw new AssertionError(card.getName());
      }
      if(mode==AdventureModes.Standard && cfg.getConfigData().starterDecksByEdition.containsKey(set)){
       if(cards.size()!=40 || cards.stream().filter(c->c.getRules().getType().isLand()).count()<14)throw new AssertionError("mana base");
       for(var pc:cards)if(!allowed.contains(pc.getEdition()))throw new AssertionError(pc.getName());
      }
      long bad=cards.stream().filter(c->!allowed.contains(c.getEdition())).count();
      if(bad!=0 || deck.getMain().countAll()<40)failures++;
      System.out.println("STARTCHECK "+level.name+" "+mode+" "+set+" "+color+" "+(bad==0&&deck.getMain().countAll()>=40?"OK":"INVALID")+" "+cards.size()+" "+bad);
     }catch(Exception e){failures++;System.out.println("STARTCHECK "+level.name+" "+mode+" "+set+" "+color+" ERROR "+e);}
    }
   }
  }
  if (failures == 0 && args.length == 3 && args[2].equals("--battles"))
      for (var group : groups.entrySet()) battleGroup(new ArrayList<>(group.getValue().entrySet()), group.getKey().equals("commander"));
  System.exit(failures==0?0:1);
 }
}
