import java.nio.file.*;
import java.util.*;
import forge.gui.GuiBase;
import forge.adventure.util.*;
import forge.adventure.data.*;
import forge.localinstance.properties.ForgeConstants;
import forge.model.FModel;
public class Starts {
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
    for(String set:(mode==AdventureModes.Standard?cfg.starterEditions():new String[]{"DMU"}))for(String color:cfg.colorIds()){
     try{
      var deck=cfg.starterDeck(forge.card.ColorSet.fromNames(color.toCharArray()),level,mode,0,FModel.getMagicDb().getEditions().get(set));
      var cards=deck.getAllCardsInASinglePool().toFlatList();if(mode==AdventureModes.Commander){
       var leaders=deck.getCommanders(); if(leaders.size()!=1||!leaders.get(0).getRules().canBeCommander()||cards.size()!=100)throw new AssertionError("commander");
       int leader=leaders.get(0).getRules().getColorIdentity().getColor(); var seen=new HashSet<String>(); for(var card:cards)if((card.getRules().getColorIdentity().getColor() & ~leader)!=0||(!card.getRules().getType().isBasicLand() && !seen.add(card.getName())))throw new AssertionError(card.getName());
      }
      if(mode==AdventureModes.Standard && cfg.getConfigData().starterDecksByEdition.containsKey(set)){
       if(cards.size()!=40 || cards.stream().filter(c->c.getRules().getType().isLand()).count()!=17)throw new AssertionError("mana base");
       int mask=forge.card.ColorSet.fromNames(color.toCharArray()).getColor();
       for(var pc:cards)if((pc.getRules().getColorIdentity().getColor() & ~mask)!=0 || !(pc.getEdition().equals(set) || set.equals("MAT")&&pc.getEdition().equals("MOM")))throw new AssertionError(pc.getName());
      }
      long bad=cards.stream().filter(c->!allowed.contains(c.getEdition())).count();
      if(bad!=0 || deck.getMain().countAll()<40)failures++;
      System.out.println("STARTCHECK "+level.name+" "+mode+" "+set+" "+color+" "+(bad==0&&deck.getMain().countAll()>=40?"OK":"INVALID")+" "+cards.size()+" "+bad);
     }catch(Exception e){failures++;System.out.println("STARTCHECK "+level.name+" "+mode+" "+set+" "+color+" ERROR "+e);}
    }
   }
  }System.exit(failures==0?0:1);
 }
}
