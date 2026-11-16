import java.nio.file.*;
import java.util.*;
import forge.gui.GuiBase;
import forge.adventure.util.*;
import forge.adventure.data.*;
import forge.localinstance.properties.ForgeConstants;
import forge.model.FModel;
public class Starts {
 static void verifyFixed(Config cfg, String ref, forge.deck.Deck deck) throws Exception {
  var expected=new TreeMap<String,Integer>();
  String section="";
  for(String row:Files.readAllLines(cfg.getFile(ref).file().toPath())){
   if(row.startsWith("["))section=row.toLowerCase(Locale.ROOT);
   else if(row.matches("[0-9]+ .*")){
    var parts=row.split(" ",2);
    expected.merge(section+" "+parts[1],Integer.parseInt(parts[0]),Integer::sum);
   }
  }
  var actual=new TreeMap<String,Integer>();
  for(var part:deck)for(var pc:part.getValue().toFlatList()){
   String sectionName=part.getKey().name().toLowerCase(Locale.ROOT);
   actual.merge("["+sectionName+"] "+pc.getName()+"|"+pc.getEdition()+"|"+pc.getArtIndex(),1,Integer::sum);
  }
  if(!actual.equals(expected))throw new AssertionError("DCK mismatch "+ref);
 }
 public static void main(String[] args) throws Exception {
  GuiBase.setInterface(new forge.GuiDesktop());
  FModel.initialize(null,null);
  Path settings=Path.of(ForgeConstants.USER_ADVENTURE_DIR,"settings.json");
  if (!settings.toAbsolutePath().normalize().startsWith(Path.of("").toAbsolutePath())) throw new AssertionError(settings);
  Files.createDirectories(settings.getParent());
  Files.writeString(settings,"{\"plane\":\""+args[0]+"\"}");
  Config cfg=Config.instance();
  if(!cfg.getPlane().equals(args[0]) || WorldData.getAllEnemies().size!=464) throw new AssertionError(cfg.getPlane());
  System.out.println("PLANE "+cfg.getPlane()+" "+cfg.getFile("world/enemies.json"));
  if(args[0].equals("Shandalar")) {System.exit(0);}
  cfg.getSettingData().useAllCardVariants=Boolean.parseBoolean(args[1]);
  var allowed=Set.of(cfg.getConfigData().allowedEditions);
  int failures=0;
  for(var level:cfg.getConfigData().difficulties){
   Current.player().updateDifficulty(level);
   for(var mode:List.of(AdventureModes.Standard,AdventureModes.Constructed,AdventureModes.Pile,AdventureModes.Commander)){
    for(String set:(mode==AdventureModes.Standard?cfg.starterEditions():new String[]{"LTR"}))for(String color:cfg.colorIds()){
     try{
      var deck=cfg.starterDeck(forge.card.ColorSet.fromNames(color.toCharArray()),level,mode,0,FModel.getMagicDb().getEditions().get(set));
      var cards=deck.getAllCardsInASinglePool().toFlatList();if(mode==AdventureModes.Commander){
       var leaders=deck.getCommanders(); if(leaders.size()!=1||!leaders.get(0).getRules().canBeCommander()||cards.size()!=100)throw new AssertionError("commander");
       int leader=leaders.get(0).getRules().getColorIdentity().getColor(); var seen=new HashSet<String>(); for(var card:cards)if((card.getRules().getColorIdentity().getColor() & ~leader)!=0||(!card.getRules().getType().isBasicLand() && !seen.add(card.getName())))throw new AssertionError(card.getName());
      }
      if(mode==AdventureModes.Standard && cfg.getConfigData().starterDecksByEdition.containsKey(set)){
       if(cards.size()!=40 || cards.stream().filter(c->c.getRules().getType().isLand()).count()!=17)throw new AssertionError("mana base");
       int mask=forge.card.ColorSet.fromNames(color.toCharArray()).getColor();
       for(var pc:cards)if((pc.getRules().getColorIdentity().getColor() & ~mask)!=0 || !(pc.getEdition().equals(set)))throw new AssertionError(pc.getName());
      }
      String fixed=mode==AdventureModes.Constructed?level.constructedStarterDecks.get(color):
        mode==AdventureModes.Commander?level.commanderDecks.get(color):
        mode==AdventureModes.Standard && cfg.getConfigData().starterDecksByEdition.containsKey(set)?
          cfg.getConfigData().starterDecksByEdition.get(set).get(color):null;
      if(fixed!=null)verifyFixed(cfg,fixed,deck);
      if(mode==AdventureModes.Standard && cards.stream().anyMatch(pc->!pc.getEdition().equals(set)))
       throw new AssertionError("Standard "+set+" "+color+" loaded "+cards.stream().map(pc->pc.getEdition()).distinct().toList());
      long bad=cards.stream().filter(c->!allowed.contains(c.getEdition())).count();
      if(bad!=0 || deck.getMain().countAll()<40)failures++;
      System.out.println("STARTCHECK "+level.name+" "+mode+" "+set+" "+color+" "+(bad==0&&deck.getMain().countAll()>=40?"OK":"INVALID")+" "+cards.size()+" "+bad);
     }catch(Exception e){failures++;System.out.println("STARTCHECK "+level.name+" "+mode+" "+set+" "+color+" ERROR "+e);}
    }
   }
  }System.exit(failures==0?0:1);
 }
}
